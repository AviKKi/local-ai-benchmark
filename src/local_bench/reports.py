import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import BenchmarkError


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path, text):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")


def format_rate(value):
    return f"{value:.2f}" if value is not None else "—"


def model_throughput_order(model):
    rate = next((profile.get("metrics", {}).get("generation_tokens_per_second")
                 for profile in model.get("profiles", []) if profile.get("id") == "single"), None)
    return (rate is None, -rate if rate is not None else 0)


def render_report(report):
    lines = ["# Benchmark Run", "", f"- Run: `{report['run_id']}`", f"- Device: `{report['device_id']}`",
             f"- Status: {report['status']}", f"- Catalog: {report['catalog_as_of']}",
             f"- Ollama: {cell(report.get('ollama_version') or 'not started')}", "",
             "Decoding throughput includes generated thinking tokens where reported by Ollama. Probes and warmups are excluded. Batch requests run sequentially. Output quality is not scored.", "",
             "| Model | Status | Profile | Decode tok/s | End-to-end tok/s | Reason |",
             "| --- | --- | --- | ---: | ---: | --- |"]
    for model in sorted(report["models"], key=model_throughput_order):
        profiles = model.get("profiles", [])
        for profile in profiles or [{}]:
            metrics = profile.get("metrics", {})
            status = "reused" if model.get("reused_from") else model["status"]
            reason = f"Measured in {model['reused_from']['run_id']}" if model.get("reused_from") else model.get("skip_or_failure_reason") or ""
            lines.append(f"| {cell(model['ollama_tag'])} | {status} | {cell(profile.get('id', '—'))} | {format_rate(metrics.get('generation_tokens_per_second'))} | {format_rate(metrics.get('end_to_end_tokens_per_second'))} | {cell(reason)} |")
    if report.get("error"):
        lines += ["", "## Run Error", "", cell(report["error"])]
    lines += ["", "## System Specifications", "", "```json", json.dumps(report.get("system_specs", {}), indent=2), "```", "",
              "Detailed per-request timings, prompts, resource peaks and missing-metric reasons are in [results.json](results.json). Events and skip reasons are in [events.jsonl](events.jsonl).", ""]
    return "\n".join(lines)


class Reports:
    def __init__(self, directory, report, maximum):
        self.directory, self.report, self.maximum = directory, report, maximum
        self.log = (directory / "events.jsonl").open("a", encoding="utf-8")
        self.written = 0

    def event(self, kind, message, **metadata):
        line = json.dumps({"time": utc_now(), "kind": kind, "message": message, **metadata}, allow_nan=False) + "\n"
        self.written += len(line.encode())
        if self.written > min(16 * 1024 * 1024, self.maximum // 8):
            raise BenchmarkError("Event log exceeded its capture budget")
        self.log.write(line)
        self.log.flush()

    def save(self):
        self.report["updated_at"] = utc_now()
        encoded = json.dumps(self.report, indent=2, allow_nan=False) + "\n"
        markdown = render_report(self.report)
        if 2 * (len(encoded.encode()) + len(markdown.encode())) + self.written > self.maximum:
            raise BenchmarkError("Reports exceed the reserved result budget")
        atomic_write(self.directory / "results.json", encoded)
        atomic_write(self.directory / "report.md", markdown)

    def close(self):
        self.log.close()


def publish(root, directory, report):
    if report["status"] != "completed" or report.get("plan_only"):
        raise BenchmarkError("Only completed measured runs can be published")
    measured = [model for model in report["models"] if model["status"] == "completed"]
    if not measured:
        raise BenchmarkError("No successfully measured models to publish")
    readme = root / "README.md"
    original = readme.read_text()
    opening, closing = "<!-- BENCHMARKS:START -->", "<!-- BENCHMARKS:END -->"
    if original.count(opening) != 1 or original.count(closing) != 1 or original.index(opening) >= original.index(closing):
        raise BenchmarkError("README markers are missing, duplicated or reversed; publication cancelled")
    target = directory / "report.md"
    relative = target.relative_to(root).as_posix()
    summary = f"\nLatest run: **{cell(report['device_id'])}** · {len(measured)} models measured. [Read the report]({relative}).\n"
    replacement = original[:original.index(opening) + len(opening)] + summary + original[original.index(closing):]
    index_path = root / "benchmarks" / "README.md"
    index = index_path.read_text()
    entry = f"- [{report['run_id']} — {cell(report['device_id'])}]({target.relative_to(root / 'benchmarks').as_posix()})"
    if entry not in index:
        if "## Run Reports\n" not in index:
            raise BenchmarkError("Benchmark index is missing its Run Reports heading")
        index = index.replace("## Run Reports\n", "## Run Reports\n\n" + entry + "\n", 1)
        index = index.replace("Results coming soon. No measured benchmark runs have been published yet.", "Measured run reports are listed below. Each report records the device, model settings, resource measurements and skipped models.")
    atomic_write(index_path, index)
    atomic_write(readme, replacement)
