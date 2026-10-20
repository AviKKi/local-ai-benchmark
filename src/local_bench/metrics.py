import math
import re

ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DURATION = re.compile(r"(\d+(?:\.\d+)?)(ns|us|µs|μs|ms|s|m|h)")
FACTORS = {"ns": 1e-9, "us": 1e-6, "µs": 1e-6, "μs": 1e-6, "ms": 1e-3, "s": 1, "m": 60, "h": 3600}


def duration_seconds(value):
    matches = list(DURATION.finditer(value.strip()))
    if not matches or "".join(match.group() for match in matches) != value.strip():
        return None
    result = sum(float(match[1]) * FACTORS[match[2]] for match in matches)
    return result if math.isfinite(result) and result > 0 else None


def rate(count, duration):
    return count / duration if count is not None and duration and duration > 0 else None


def parse_metrics(stderr, wall_seconds):
    clean = ANSI.sub("", stderr).replace("\r", "\n")
    fields = {}
    for line in clean.splitlines():
        if ":" in line:
            name, value = line.strip().split(":", 1)
            fields[name] = value.strip()

    def count(name):
        match = re.fullmatch(r"(\d+) token\(s\)", fields.get(name, ""))
        return int(match[1]) if match else None

    generated, prompt = count("eval count"), count("prompt eval count")
    cached = count("prompt eval cached")
    generation_time = duration_seconds(fields.get("eval duration", ""))
    prompt_time = duration_seconds(fields.get("prompt eval duration", ""))
    metrics = {
        "generated_tokens": generated,
        "prompt_tokens": prompt,
        "cached_prompt_tokens": cached,
        "generation_seconds": generation_time,
        "prompt_eval_seconds": prompt_time,
        "generation_tokens_per_second": rate(generated, generation_time),
        "prompt_eval_tokens_per_second": rate(max(0, prompt - (cached or 0)) if prompt is not None else None, prompt_time),
        "wall_time_seconds": wall_seconds,
        "end_to_end_tokens_per_second": rate(generated, wall_seconds),
        "model_load_seconds": duration_seconds(fields.get("load duration", "")),
    }
    metrics["missing_metric_reasons"] = {
        name: "CLI did not report a usable value (missing, unsupported, or zero duration)"
        for name, value in metrics.items() if value is None
    }
    return metrics


def aggregate(requests):
    metrics = [request["metrics"] for request in requests]
    valid = [item for item in metrics if item["generated_tokens"] is not None and item["generation_seconds"]]
    generated = sum(item["generated_tokens"] for item in valid)
    seconds = sum(item["generation_seconds"] for item in valid)
    wall = sum(item["wall_time_seconds"] for item in metrics)
    complete_counts = all(item["generated_tokens"] is not None for item in metrics)
    return {
        "requests": len(requests),
        "valid_generation_measurements": len(valid),
        "generated_tokens": sum(item["generated_tokens"] for item in metrics) if complete_counts else None,
        "generation_tokens_per_second": rate(generated, seconds),
        "wall_time_seconds": wall,
        "end_to_end_tokens_per_second": rate(sum(item["generated_tokens"] for item in metrics), wall) if complete_counts else None,
        "aggregation": "sum of valid generated tokens / sum of their generation durations; warmup and probes excluded",
    }
