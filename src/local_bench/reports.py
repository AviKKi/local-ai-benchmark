import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import BenchmarkError


MAXIMUM_REPORT_BYTES = 16 * 1024 * 1024


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


def replace_marked_region(text, opening, closing, content, name):
    if text.count(opening) != 1 or text.count(closing) != 1 or text.index(opening) >= text.index(closing):
        raise BenchmarkError(f"{name} markers are missing, duplicated or reversed; publication cancelled")
    start = text.index(opening) + len(opening)
    end = text.index(closing)
    return text[:start] + "\n" + content + "\n" + text[end:]


def report_timestamp(report):
    return str(report.get("started_at") or report.get("run_id") or "")


def read_saved_reports(root, warning):
    runs = (Path(root) / "benchmarks" / "runs").resolve()
    reports = []
    if not runs.is_dir():
        return reports
    for path in runs.glob("*/*/results.json"):
        try:
            if path.is_symlink() or not path.resolve().is_relative_to(runs):
                raise ValueError("report is outside the benchmark archive")
            report_path = path.parent / "report.md"
            if report_path.is_symlink() or not report_path.is_file() or not report_path.resolve().is_relative_to(runs):
                raise ValueError("report.md is missing or outside the benchmark archive")
            with path.open("rb") as stream:
                raw = stream.read(MAXIMUM_REPORT_BYTES + 1)
            if len(raw) > MAXIMUM_REPORT_BYTES:
                raise ValueError("results file exceeds the read limit")
            report = json.loads(raw)
            if (not isinstance(report, dict) or not isinstance(report.get("run_id"), str)
                    or not report["run_id"] or not isinstance(report.get("device_id"), str)
                    or not report["device_id"] or not isinstance(report.get("models"), list)):
                raise ValueError("results must contain run_id, device_id and a models list")
            reports.append({"path": path, "report_path": report_path, "report": report})
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            warning(f"Ignoring unreadable benchmark report {path}: {error}")
    return sorted(reports, key=lambda item: (report_timestamp(item["report"]), str(item["path"])), reverse=True)


def profile_rate(model, profile_id):
    for profile in model.get("profiles", []):
        if isinstance(profile, dict) and profile.get("id") == profile_id:
            rate = profile.get("metrics", {}).get("generation_tokens_per_second")
            if isinstance(rate, (int, float)) and not isinstance(rate, bool) and math.isfinite(rate):
                return rate
    return None


def latest_measurements(reports):
    direct, reused = {}, {}
    for saved in reports:
        report = saved["report"]
        if report.get("plan_only"):
            continue
        for model in report["models"]:
            if not isinstance(model, dict) or model.get("status") != "completed":
                continue
            model_id = model.get("model_id")
            if not isinstance(model_id, str) or not model_id:
                continue
            target = reused if model.get("reused_from") else direct
            target.setdefault(model_id, (saved, model))
    return list((direct | {key: value for key, value in reused.items() if key not in direct}).values())


def render_highlights(measurements, root):
    lines = ["Latest completed measurement for each model from saved runs.", "",
             "| Model | Device | Single decode tok/s | Sequential batch decode tok/s | Source |",
             "| --- | --- | ---: | ---: | --- |"]
    ordered = sorted(measurements, key=lambda item: (
        profile_rate(item[1], "single") is None,
        -(profile_rate(item[1], "single") or 0),
        item[1].get("model_id", ""), item[0]["report"].get("device_id", ""),
    ))
    for saved, model in ordered:
        report = saved["report"]
        source = saved["report_path"].relative_to(root).as_posix()
        lines.append(f"| {cell(model.get('ollama_tag') or model['model_id'])} | {cell(report['device_id'])} | "
                     f"{format_rate(profile_rate(model, 'single'))} | {format_rate(profile_rate(model, 'batch_sequential'))} | [report]({source}) |")
    lines += ["", "Decode throughput includes generated thinking tokens where reported. Requests run sequentially; probes and warmups are excluded. Output quality is not scored."]
    return "\n".join(lines)


def render_index(reports, root):
    lines = []
    for saved in reports:
        report = saved["report"]
        completed = sum(isinstance(model, dict) and model.get("status") == "completed" for model in report["models"])
        source = saved["report_path"].relative_to(root / "benchmarks").as_posix()
        lines.append(f"- [{report['run_id']} — {cell(report['device_id'])}]({source}) · {completed} completed model(s); run {cell(report.get('status') or 'unknown')}.")
    return "\n".join(lines)


def publish_saved(root, warning=lambda message: None):
    root = Path(root).resolve()
    reports = read_saved_reports(root, warning)
    measurements = latest_measurements(reports)
    if not measurements:
        raise BenchmarkError("No successfully measured models to publish")
    readme = root / "README.md"
    index_path = root / "benchmarks" / "README.md"
    replacement = replace_marked_region(readme.read_text(), "<!-- BENCHMARKS:START -->", "<!-- BENCHMARKS:END -->",
                                        render_highlights(measurements, root), "README")
    index = replace_marked_region(index_path.read_text(), "<!-- BENCHMARK-RUNS:START -->", "<!-- BENCHMARK-RUNS:END -->",
                                  render_index(reports, root), "Benchmark index")
    if replacement != readme.read_text():
        atomic_write(readme, replacement)
    if index != index_path.read_text():
        atomic_write(index_path, index)
    return len(measurements)


def publish(root, directory, report):
    if report["status"] != "completed" or report.get("plan_only"):
        raise BenchmarkError("Only completed measured runs can be published")
    if not any(model.get("status") == "completed" for model in report["models"]):
        raise BenchmarkError("No successfully measured models to publish")
    return publish_saved(root)
