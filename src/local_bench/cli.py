import argparse
import fcntl
import fnmatch
import json
import os
import re
import shutil
import signal
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import psutil
from rich.console import Console

from .config import BenchmarkError, CleanupError, SafetyError, load_catalog
from .engine import Ollama
from .downloads import execute_pairs
from .history import choose_resume, measurement_signature, read_history, reusable_measurements
from .metrics import aggregate
from .processes import CommandRunner, cleanup_signals
from .prompts import PROMPTS, validate_prompts
from .registry import Registry
from .reports import Reports, publish, publish_saved, utc_now
from .safety import Guard, disk_reason, memory_budget, memory_reason
from .system import MacTelemetry
from .ui import Dashboard


@contextmanager
def run_workspace(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / "run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BenchmarkError("Another benchmark holds the workspace lock") from error
        workspace = Path(tempfile.mkdtemp(prefix="run-", dir=root)).resolve()
        try:
            yield workspace
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def parser():
    result = argparse.ArgumentParser(description="Safely benchmark the models.json catalog using an isolated Ollama CLI server.")
    result.add_argument("--models-file", type=Path, default=Path("models.json"))
    result.add_argument("--model", action="append", default=[], help="Model ID/tag or glob; repeat to select multiple")
    result.add_argument("--limit", type=int, help="Maximum statically eligible models to attempt")
    result.add_argument("--plan", action="store_true", help="Local RAM/disk checks only; no install, registry request or model download")
    result.add_argument("--no-ui", action="store_true", help="Plain progress events, suitable for logs/CI")
    result.add_argument("--device", help="Filesystem-safe device label; default derives from model and RAM, excluding serial numbers")
    result.add_argument("--work-dir", type=Path, default=Path(".benchmark-work"))
    result.add_argument("--output-dir", type=Path, default=Path("benchmarks/runs"))
    result.add_argument("--publish", action="store_true", help="Update README highlights and the benchmark index after a completed measured run")
    result.add_argument("--publish-only", action="store_true", help="Regenerate README highlights and the benchmark index from saved benchmark reports")
    result.add_argument("--download-workers", type=int, choices=(1, 2), help="Download one model or a pair before serial inference; default follows catalog (2)")
    mode = result.add_mutually_exclusive_group()
    mode.add_argument("--resume", action="store_true", help="Reuse completed compatible measurements for this system; retry skipped, failed and unfinished models")
    mode.add_argument("--fresh", action="store_true", help="Benchmark selected models again without reusing history")
    return result


def model_record(model, catalog):
    return {
        "model_id": model["id"], "ollama_tag": model["ollama_tag"], "status": "pending",
        "catalog_schema_version": catalog["schema_version"], "catalog_as_of": catalog["as_of"],
        "resolved_manifest_sha256": None, "actual_quantization": None,
        "actual_context_length": None, "actual_backend": None,
        "thinking_mode": "model_default (no CLI override; effective reasoning effort is not exposed by the CLI)",
        "memory_budget_bytes": memory_budget(model, catalog["policy"]),
        "skip_or_failure_reason": None, "probes": [], "warmups": [], "profiles": [], "metrics": {},
    }


def benchmark_model(engine, guard, model, record, catalog, ui, save, aliases):
    ui.update(stage=f"{model['ollama_tag']} · preparing one-token probes")
    probe_alias = engine.create_alias(model, probe=True)
    aliases.append(probe_alias)
    record["actual_quantization"] = engine.inspect(probe_alias, model["quantization"])
    for index, prompt in enumerate(PROMPTS):
        guard.admit(resident=index > 0, disk=False)
        ui.update(stage=f"{model['ollama_tag']} · prompt probe {prompt.category}")
        metrics = engine.request(probe_alias, prompt.text, first_load=index == 0)
        if metrics["generated_tokens"] is not None and metrics["generated_tokens"] > 1:
            raise SafetyError("One-token probe limit was not enforced")
        record["probes"].append({"prompt_id": prompt.id, "metrics": metrics})
        save()
    engine.unload(probe_alias)
    guard.admit(disk=False)
    alias = engine.create_alias(model)
    aliases.append(alias)
    for index in range(catalog["benchmark"]["warmup_requests"]):
        prompt = PROMPTS[index % len(PROMPTS)]
        guard.admit(resident=index > 0, disk=False)
        ui.update(stage=f"{model['ollama_tag']} · warmup {index+1}")
        record["warmups"].append({"prompt_id": prompt.id, "metrics": engine.request(alias, prompt.text, first_load=index == 0)})
    record["actual_context_length"] = catalog["benchmark"]["options"]["num_ctx"]
    record["actual_backend"] = "metal (ollama ps: 100% GPU)"
    for profile in catalog["benchmark"]["profiles"]:
        measured = {"id": profile["id"], "benchmark_profile": profile["id"], "concurrency": 1, "requests": [], "metrics": {}}
        record["profiles"].append(measured)
        for index in range(profile["measured_requests"]):
            prompt = PROMPTS[index % len(PROMPTS)]
            guard.admit(resident=True, disk=False)
            ui.update(stage=f"{model['ollama_tag']} · {profile['id']} {index+1}/{profile['measured_requests']} · {prompt.category}")
            metrics = engine.request(alias, prompt.text)
            measured["requests"].append({"prompt_id": prompt.id, "category": prompt.category, "metrics": metrics})
            measured["metrics"] = aggregate(measured["requests"])
            save()
        metrics = measured["metrics"]
        throughput = metrics["generation_tokens_per_second"]
        ui.event("throughput", f"{model['ollama_tag']} · {profile['id']}: {throughput:.2f} tok/s" if throughput is not None else f"{model['ollama_tag']} · {profile['id']}: timing unavailable")


def execute(args, catalog, models, telemetry, specs, report, reports, ui, workspace, reusable=None):
    if args.download_workers == 2 and not args.plan:
        return execute_pairs(args, catalog, models, telemetry, specs, report, reports, ui, workspace, reusable,
                             model_record, benchmark_model, Ollama)

    def event(kind, message):
        reports.event(kind, message)
        ui.event(kind, message)

    commands = CommandRunner(catalog["policy"], workspace, event)
    engine = Ollama(catalog, commands, workspace, reports.directory)
    attempts = 0
    try:
        for model in models:
            previous = (reusable or {}).get(model["ollama_tag"])
            if previous is not None:
                report["models"].append(previous)
                event("reused", f"{model['ollama_tag']}: already benchmarked in {previous['reused_from']['run_id']}; no download or inference")
                ui.finish("reused")
                reports.save()
                continue
            record = model_record(model, catalog)
            report["models"].append(record)
            reason = None
            if not model["enabled"]:
                reason = "disabled:" + (model.get("disabled_reason") or "disabled in catalog")
            elif model["compatibility"]["backend"] != "metal" or specs["os"].lower() not in model["compatibility"]["os"] or specs["architecture"] not in model["compatibility"]["architectures"]:
                reason = "incompatible_host_or_backend"
            elif args.limit is not None and attempts >= args.limit:
                reason = "cli_model_limit_reached"
            else:
                reason = memory_reason(model, catalog["policy"], telemetry.snapshot()) or disk_reason(model, catalog["policy"], engine.paths)
            if reason:
                record.update(status="skipped", skip_or_failure_reason=reason)
                event("skipped", f"{model['ollama_tag']}: {reason}")
                ui.finish("skipped")
                reports.save()
                continue
            attempts += 1
            if args.plan:
                record.update(status="planned", skip_or_failure_reason="local_admission_passed; manifest, installed backend and live load remain unverified")
                event("planned", model["ollama_tag"])
                ui.finish("planned")
                reports.save()
                continue
            record["status"] = "running"
            reports.save()
            aliases = []
            guard = Guard(telemetry, model, catalog["policy"], engine.paths, reports.directory, engine.store,
                          commands.processes, lambda sample: ui.update(sample=sample))
            commands.guard = guard
            try:
                guard.admit()
                ui.update(stage=f"{model['ollama_tag']} · verifying registry manifest")
                manifest = Registry(catalog["policy"], commands).resolve(model, guard)
                record["resolved_manifest_sha256"] = manifest.digest
                record["download_payload_bytes"] = manifest.payload_bytes
                ui.update(stage=f"{model['ollama_tag']} · checking/installing Ollama")
                engine.install()
                guard.admit()
                engine.start()
                report["ollama_version"] = engine.version
                record["ollama_version"] = engine.version
                ui.update(stage=f"{model['ollama_tag']} · downloading")
                guard.admit()
                engine.pull(model, manifest)
                benchmark_model(engine, guard, model, record, catalog, ui, reports.save, aliases)
                if not any(profile["metrics"].get("valid_generation_measurements", 0) for profile in record["profiles"]):
                    raise BenchmarkError("No usable generation timings were reported")
                record["status"] = "completed"
                event("completed", model["ollama_tag"])
            except KeyboardInterrupt:
                record.update(status="interrupted", skip_or_failure_reason="user_interrupt")
                raise
            except (BenchmarkError, OSError) as error:
                status = "failed" if record["probes"] or record["warmups"] or record["profiles"] else "skipped"
                record.update(status=status, skip_or_failure_reason=str(error))
                event(status, f"{model['ollama_tag']}: {error}")
            finally:
                record["metrics"] = guard.metrics()
                ui.update(stage=f"{model['ollama_tag']} · cleanup")
                with cleanup_signals():
                    engine.clear_model(aliases, model["ollama_tag"], record["status"] == "completed")
                reason = disk_reason(model, catalog["policy"], engine.paths, admission=False)
                if reason:
                    raise CleanupError("Disk reserve not restored after cleanup: " + reason)
                reports.save()
            ui.finish(record["status"])
        report["status"] = "planned" if args.plan else "completed"
    finally:
        commands.guard = None
        with cleanup_signals():
            engine.stop_server()
            if workspace.is_symlink():
                raise CleanupError("Owned workspace became a symlink; refusing recursive deletion")
            shutil.rmtree(workspace)


def run(args):
    root = args.models_file.resolve().parent
    if args.publish_only:
        if args.plan or args.publish or args.resume or args.fresh or args.model or args.limit is not None or args.device or args.download_workers:
            raise BenchmarkError("--publish-only cannot be combined with benchmark execution options")
        published = publish_saved(root, lambda message: Console().print(message, markup=False))
        Console().print(f"Published {published} latest model measurements from saved reports", markup=False)
        return 0
    if args.limit is not None and args.limit < 1:
        raise BenchmarkError("--limit must be positive")
    if args.plan and args.publish:
        raise BenchmarkError("--plan cannot publish measurements")
    if args.plan and args.resume:
        raise BenchmarkError("--plan cannot reuse measurements; omit --resume")
    if args.device and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", args.device):
        raise BenchmarkError("--device must be a filesystem-safe label")
    catalog = load_catalog(args.models_file)
    args.download_workers = args.download_workers or catalog["policy"]["execution"]["max_concurrent_downloads"]
    if args.download_workers > catalog["policy"]["execution"]["max_concurrent_downloads"]:
        raise BenchmarkError("--download-workers exceeds the catalog download limit")
    validate_prompts()
    models = [model for model in catalog["models"] if not args.model or any(
        fnmatch.fnmatchcase(model["id"], pattern) or fnmatch.fnmatchcase(model["ollama_tag"], pattern)
        for pattern in args.model)]
    if not models:
        raise BenchmarkError("No models matched --model")
    models.sort(key=lambda model: (not model["enabled"], model["resources"]["download_bytes_upper_bound"], model["id"]))
    if args.publish and not args.output_dir.resolve().is_relative_to(root / "benchmarks" / "runs"):
        raise BenchmarkError("--publish requires output inside this project's benchmarks/runs")
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S.%fZ")
    telemetry, specs, setup_error = None, {}, None
    try:
        telemetry = MacTelemetry()
        specs = telemetry.specs()
    except (BenchmarkError, OSError) as error:
        setup_error = str(error)
    default_device = f"{specs.get('model') or 'macos-arm64'}-{specs.get('memory', {}).get('physical', 0)//1024**3}gib"
    device_id = args.device or re.sub(r"[^a-zA-Z0-9._-]", "-", default_device).lower()
    console = Console()
    warning = lambda message: console.print(message, markup=False)
    history = []
    resume = args.resume
    if not setup_error and (args.resume or getattr(args, "prompt_for_mode", False)):
        history = read_history(args.output_dir, specs, catalog, warning)
        if not args.resume:
            resume = choose_resume(history, True, sys.stdin, warning)
    reusable = reusable_measurements(history, models, catalog, warning) if resume else {}
    if resume:
        warning(f"Resume: reusing {len(reusable)} completed models; remaining selected models will be checked and retried.")
    directory = args.output_dir.resolve() / device_id / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {
        "run_id": run_id, "device_id": device_id, "started_at": utc_now(), "status": "running",
        "plan_only": args.plan, "catalog_schema_version": catalog["schema_version"], "catalog_as_of": catalog["as_of"],
        "system_specs": specs, "ollama_version": None, "models": [],
        "benchmark_options": catalog["benchmark"]["options"],
        "measurement_signature": measurement_signature(catalog),
        "resume": resume,
        "download_workers": args.download_workers,
        "download_strategy": "bounded pairs before serial inference; no downloads during measurements" if args.download_workers == 2 else "serial",
        "prompts": [vars(prompt) for prompt in PROMPTS],
        "notes": ["No output quality evaluation; generation text is not retained.",
                  "Native model templates and default thinking behavior are retained.",
                  "One-token prompt probes run under the 2048-token context bound before measurement.",
                  "Prompt caches may remain warm between fresh-conversation CLI invocations."],
    }
    reports = Reports(directory, report, catalog["policy"]["disk"]["maximum_total_results_bytes"])
    exit_code = 0
    try:
        reports.save()
        with Dashboard(len(models), not args.no_ui) as ui:
            try:
                if setup_error:
                    raise SafetyError(setup_error)
                with run_workspace(args.work_dir.resolve()) as workspace:
                    execute(args, catalog, models, telemetry, specs, report, reports, ui, workspace, reusable)
            except KeyboardInterrupt:
                report.update(status="interrupted", error="Interrupted; owned processes and artifacts were cleaned up unless a cleanup error is reported")
                reports.event("interrupted", "User interrupt")
                exit_code = 130
            except (BenchmarkError, OSError, psutil.Error) as error:
                report.update(status="failed", error=str(error))
                reports.event("fatal", str(error))
                ui.event("fatal", str(error))
                exit_code = 1
            report["finished_at"] = utc_now()
            reports.save()
        if args.publish and exit_code == 0:
            publish(root, directory, report)
    finally:
        reports.close()
    Console().print(f"Reports: {directory}", markup=False)
    return exit_code


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else list(argv)
    args = parser().parse_args(arguments)
    args.prompt_for_mode = not (args.resume or args.fresh or args.plan or args.publish_only) and (
        not arguments or sys.stdin.isatty()
    )
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    try:
        return run(args)
    except (BenchmarkError, OSError, ValueError) as error:
        Console(stderr=True).print(f"Error: {error}", markup=False)
        return 2
    finally:
        signal.signal(signal.SIGTERM, previous)
