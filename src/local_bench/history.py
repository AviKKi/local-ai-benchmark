import copy
import hashlib
import json
import math
from pathlib import Path

from .config import BenchmarkError
from .prompts import PROMPTS


MAXIMUM_HISTORY_BYTES = 16 * 1024 * 1024


def system_identity(specs):
    return {**{key: specs.get(key) for key in (
        "os", "os_version", "architecture", "model", "chip", "logical_cpu_count", "physical_cpu_count",
    )}, "physical_memory_bytes": specs.get("memory", {}).get("physical")}


def measurement_signature(catalog):
    settings = {"benchmark": catalog["benchmark"], "prompts": [vars(prompt) for prompt in PROMPTS]}
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()


def compatible_history(report, specs, catalog):
    if report.get("plan_only") or system_identity(report.get("system_specs", {})) != system_identity(specs):
        return False
    if report.get("catalog_schema_version") != catalog["schema_version"]:
        return False
    if report.get("benchmark_options") != catalog["benchmark"]["options"]:
        return False
    if report.get("prompts") != [vars(prompt) for prompt in PROMPTS]:
        return False
    signature = report.get("measurement_signature")
    return signature is None or signature == measurement_signature(catalog)


def completed_measurement(record, model, catalog):
    if record.get("status") != "completed" or record.get("model_id") != model["id"]:
        return False
    digest = record.get("resolved_manifest_sha256")
    if not isinstance(digest, str) or not digest.startswith(model["provenance"]["observed_manifest_sha256_prefix"]):
        return False
    if model["quantization"] and str(record.get("actual_quantization", "")).casefold() != model["quantization"].casefold():
        return False
    if record.get("actual_context_length") != catalog["benchmark"]["options"]["num_ctx"]:
        return False
    profiles = record.get("profiles", [])
    if not isinstance(profiles, list) or len(profiles) != len(catalog["benchmark"]["profiles"]):
        return False
    for expected, actual in zip(catalog["benchmark"]["profiles"], profiles):
        metrics = actual.get("metrics", {})
        rate = metrics.get("generation_tokens_per_second")
        if (actual.get("id") != expected["id"] or actual.get("concurrency") != expected["concurrency"]
                or len(actual.get("requests", [])) != expected["measured_requests"]
                or metrics.get("valid_generation_measurements") != expected["measured_requests"]
                or not isinstance(rate, (int, float)) or isinstance(rate, bool)
                or not math.isfinite(rate) or rate <= 0):
            return False
    return True


def read_history(output_dir, specs, catalog, warning):
    root = Path(output_dir).resolve()
    history = []
    for path in sorted(root.glob("*/*/results.json"), reverse=True):
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            with path.open("rb") as stream:
                raw = stream.read(MAXIMUM_HISTORY_BYTES + 1)
            if len(raw) > MAXIMUM_HISTORY_BYTES:
                raise ValueError("history file exceeds the read limit")
            report = json.loads(raw)
            if not isinstance(report, dict) or not isinstance(report.get("models"), list):
                raise ValueError("history must be a JSON object with a models list")
            if compatible_history(report, specs, catalog):
                history.append((path, report))
        except (OSError, ValueError, TypeError, AttributeError) as error:
            warning(f"Ignoring unreadable history {path}: {error}")
    return sorted(history, key=lambda item: str(item[1].get("started_at", "")), reverse=True)


def reusable_measurements(history, models, catalog, warning):
    selected = {model["ollama_tag"]: model for model in models}
    reusable = {}
    for path, report in history:
        for record in report.get("models", []):
            try:
                tag = record.get("ollama_tag")
                if tag not in selected or tag in reusable or not completed_measurement(record, selected[tag], catalog):
                    continue
                copied = copy.deepcopy(record)
                copied["reused_from"] = record.get("reused_from") or {
                    "run_id": report["run_id"], "results_path": str(path.resolve()),
                    "ollama_version": record.get("ollama_version") or report.get("ollama_version"),
                }
                reusable[tag] = copied
            except (KeyError, TypeError, AttributeError) as error:
                warning(f"Ignoring malformed model history in {path}: {error}")
    return reusable


def choose_resume(history, interactive, input_stream, output):
    if not history:
        output("No compatible previous run found; starting fresh.")
        return False
    if not interactive or not input_stream.isatty():
        raise BenchmarkError("Run history exists but no interactive terminal is available; use --resume or --fresh")
    output(f"Latest compatible run: {history[0][1]['run_id']}. Resume reuses completed measurements across compatible runs.")
    while True:
        output("[R]esume previous results or benchmark [F]resh? [R/f] ")
        answer = input_stream.readline()
        if not answer:
            raise BenchmarkError("No selection received; use --resume or --fresh")
        answer = answer.strip().lower()
        if answer in ("", "r", "resume"):
            return True
        if answer in ("f", "fresh"):
            return False
