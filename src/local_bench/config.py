import json
import math
import re
from pathlib import Path


class BenchmarkError(Exception):
    pass


class SafetyError(BenchmarkError):
    pass


class CleanupError(BenchmarkError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BenchmarkError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def positive(value, name, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise BenchmarkError(f"{name} must be numeric")
    if not math.isfinite(value) or value <= 0 or (maximum and value > maximum):
        raise BenchmarkError(f"Invalid {name}: {value}")
    return value


def load_catalog(path):
    try:
        catalog = json.loads(Path(path).read_text(), object_pairs_hook=unique_object)
        validate_catalog(catalog)
        return catalog
    except (KeyError, TypeError, ValueError, OSError) as error:
        raise BenchmarkError(f"Invalid catalog: {error}") from error


def validate_catalog(catalog):
    if catalog["schema_version"] != "1.0.0":
        raise BenchmarkError("Only catalog schema 1.0.0 is supported")
    scope = catalog["scope"]
    if scope["engine"] != "ollama" or scope["interface"] != "cli":
        raise BenchmarkError("This runner only supports the Ollama CLI")
    if scope["os"] != ["darwin"] or scope["architectures"] != ["arm64"]:
        raise BenchmarkError("This runner only supports Apple Silicon macOS")
    if scope["network_inference_allowed"] or catalog["policy"]["allow_cloud_fallback"]:
        raise BenchmarkError("Cloud inference is forbidden")
    policy = catalog["policy"]
    for section in ("memory", "disk", "execution", "watchdog", "integrity"):
        for name, value in policy[section].items():
            if isinstance(value, (float, int)) and not isinstance(value, bool) and name != "max_retries_per_model":
                positive(value, f"policy.{section}.{name}")
    for name in ("maximum_physical_memory_fraction", "maximum_metal_working_set_fraction_if_reported"):
        positive(policy["memory"][name], name, 1)
    positive(policy["disk"]["reserve_volume_fraction"], "disk reserve fraction", 1)
    if policy["memory"]["estimate_multiplier"] < 1:
        raise BenchmarkError("Memory multiplier cannot be below one")
    if type(policy["execution"]["max_concurrent_downloads"]) is not int or policy["execution"]["max_concurrent_downloads"] not in (1, 2):
        raise BenchmarkError("Only one or two concurrent downloads are supported")
    for name in ("max_loaded_models", "max_parallel_requests"):
        if policy["execution"][name] != 1:
            raise BenchmarkError("Concurrent loaded models/requests are unsupported")
    if policy["execution"]["max_retries_per_model"] != 0:
        raise BenchmarkError("Automatic model retries are unsupported")
    options = catalog["benchmark"]["options"]
    expected = {"num_ctx": 2048, "num_predict": 256, "num_batch": 128, "temperature": 0, "seed": 42}
    if options != expected:
        raise BenchmarkError("Resource estimates only cover the catalog's fixed 2048/256/128 settings")
    if catalog["engine"]["modelfile_template"] != modelfile("{ollama_tag}"):
        raise BenchmarkError("Unexpected Modelfile: resource assumptions must stay fixed")
    environment = catalog["engine"]["server_environment"]
    required_environment = {"OLLAMA_HOST": "127.0.0.1:11435", "OLLAMA_NO_CLOUD": "1",
                            "OLLAMA_MAX_LOADED_MODELS": "1", "OLLAMA_NUM_PARALLEL": "1",
                            "OLLAMA_MAX_QUEUE": "1", "OLLAMA_CONTEXT_LENGTH": "2048",
                            "OLLAMA_KV_CACHE_TYPE": "f16", "OLLAMA_KEEP_ALIVE": "120s"}
    if any(environment.get(name) != value for name, value in required_environment.items()):
        raise BenchmarkError("Server environment conflicts with the resource/concurrency policy")
    positive(catalog["benchmark"]["maximum_rendered_prompt_tokens"], "prompt limit", 1024)
    positive(catalog["benchmark"]["warmup_requests"], "warmup requests", 10)
    if not isinstance(catalog["benchmark"]["warmup_requests"], int):
        raise BenchmarkError("Warmup request count must be an integer")
    profile_ids = set()
    for profile in catalog["benchmark"]["profiles"]:
        if profile["id"] in profile_ids or profile["concurrency"] != 1:
            raise BenchmarkError("Duplicate profile or unsupported concurrency")
        profile_ids.add(profile["id"])
        positive(profile["measured_requests"], "profile requests", 100)
        if not isinstance(profile["measured_requests"], int):
            raise BenchmarkError("Profile request counts must be integers")
    if not profile_ids:
        raise BenchmarkError("No benchmark profiles configured")
    identifiers, tags = set(), set()
    for model in catalog["models"]:
        identifier, tag = model["id"], model["ollama_tag"]
        if not re.fullmatch(r"[a-z0-9-]+", identifier) or identifier in identifiers:
            raise BenchmarkError(f"Invalid or duplicate model ID: {identifier}")
        if not re.fullmatch(r"[a-z0-9.-]+:[a-zA-Z0-9_.-]+", tag) or tag in tags:
            raise BenchmarkError(f"Invalid or duplicate model tag: {tag}")
        if "cloud" in tag or tag.endswith(":latest") or model["execution"] != "local":
            raise BenchmarkError(f"Not an explicit local model: {tag}")
        if model["artifact_format"] != "gguf" or model["benchmark_modalities"] != ["text"]:
            raise BenchmarkError(f"Unsupported artifact or modality: {tag}")
        if not isinstance(model["enabled"], bool):
            raise BenchmarkError("Model enabled must be boolean")
        identifiers.add(identifier)
        tags.add(tag)
        for name in ("published_download_bytes_approx", "download_bytes_upper_bound", "estimated_peak_unified_memory_bytes", "minimum_physical_memory_bytes"):
            value = model["resources"][name]
            positive(value, name)
            if not isinstance(value, int):
                raise BenchmarkError(f"{name} must be integer bytes")
        prefix = model["provenance"]["observed_manifest_sha256_prefix"]
        if not re.fullmatch(r"[a-f0-9]{12,64}", prefix):
            raise BenchmarkError(f"Invalid manifest digest: {tag}")
        family, revision = tag.split(":")
        expected_url = f"https://registry.ollama.ai/v2/library/{family}/manifests/{revision}"
        if model["provenance"]["manifest_url"] != expected_url:
            raise BenchmarkError(f"Unexpected registry URL: {tag}")
    if not tags:
        raise BenchmarkError("Empty model catalog")


def modelfile(tag, output_tokens=256):
    return (
        f"FROM {tag}\nPARAMETER num_ctx 2048\nPARAMETER num_predict {output_tokens}\n"
        "PARAMETER num_batch 128\nPARAMETER temperature 0\nPARAMETER seed 42\n"
    )
