import copy
import shutil
import time

from .config import BenchmarkError, CleanupError
from .processes import CommandRunner, cleanup_signals
from .registry import Registry
from .safety import Guard, disk_reason, memory_budget, memory_reason


def storage_model(models, policy):
    combined = copy.deepcopy(max(models, key=lambda model: memory_budget(model, policy)))
    combined["resources"]["download_bytes_upper_bound"] = sum(model["resources"]["download_bytes_upper_bound"] for model in models)
    return combined


def execute_pairs(args, catalog, models, telemetry, specs, report, reports, ui, workspace, reusable, make_record, benchmark, engine_factory):
    policy = catalog["policy"]

    def event(kind, message):
        reports.event(kind, message)
        ui.event(kind, message)

    def finish(model, record, status, reason=None):
        record.update(status=status, skip_or_failure_reason=reason)
        event(status, f"{model['ollama_tag']}: {reason}" if reason else model["ollama_tag"])
        ui.finish(status)
        reports.save()

    commands = CommandRunner(policy, workspace, event)
    engine = engine_factory(catalog, commands, workspace, reports.directory)

    def admitted_jobs():
        attempts = 0
        for model in models:
            previous = (reusable or {}).get(model["ollama_tag"])
            if previous is not None:
                report["models"].append(previous)
                event("reused", f"{model['ollama_tag']}: already benchmarked in {previous['reused_from']['run_id']}; no download or inference")
                ui.finish("reused")
                reports.save()
                continue
            record = make_record(model, catalog)
            report["models"].append(record)
            reason = None
            if not model["enabled"]:
                reason = "disabled:" + (model.get("disabled_reason") or "disabled in catalog")
            elif model["compatibility"]["backend"] != "metal" or specs["os"].lower() not in model["compatibility"]["os"] or specs["architecture"] not in model["compatibility"]["architectures"]:
                reason = "incompatible_host_or_backend"
            elif args.limit is not None and attempts >= args.limit:
                reason = "cli_model_limit_reached"
            else:
                reason = memory_reason(model, policy, telemetry.snapshot()) or disk_reason(model, policy, engine.paths)
            if reason:
                finish(model, record, "skipped", reason)
                continue
            attempts += 1
            record["status"] = "running"
            reports.save()
            yield model, record

    jobs = iter(admitted_jobs())
    deferred = None
    active_group = []
    try:
        while True:
            first = deferred if deferred is not None else next(jobs, None)
            deferred = None
            if first is None:
                break
            active_group = [first]
            second = next(jobs, None)
            if second is not None:
                combined = storage_model([first[0], second[0]], policy)
                reason = disk_reason(combined, policy, engine.paths)
                if reason:
                    deferred = second
                    event("download_queue", f"Pair exceeds disk admission; falling back to one download: {reason}")
                else:
                    active_group.append(second)
            grouped_models = [model for model, _ in active_group]
            storage = storage_model(grouped_models, policy)
            batch_tags = [model["ollama_tag"] for model in grouped_models]
            batch_guard = Guard(telemetry, storage, policy, engine.paths, reports.directory, engine.store,
                                commands.processes, lambda sample: ui.update(sample=sample), storage_model=storage)
            commands.guard = batch_guard
            ready = []
            started = time.monotonic()
            try:
                batch_guard.admit()
                for model, record in active_group:
                    ui.update(stage=f"{model['ollama_tag']} · verifying registry manifest")
                    try:
                        manifest = Registry(policy, commands).resolve(model, batch_guard)
                        record["resolved_manifest_sha256"] = manifest.digest
                        record["download_payload_bytes"] = manifest.payload_bytes
                        ready.append((model, record, manifest))
                    except (BenchmarkError, OSError) as error:
                        finish(model, record, "skipped", str(error))
                if ready:
                    engine.install()
                    batch_guard.paths = engine.paths
                    batch_guard.admit()
                    engine.start()
                    report["ollama_version"] = engine.version
                    batch_guard.admit()
                    event("download_queue", f"Downloading {len(ready)} model(s); queue bounded to two, inference waits until all pulls finish")
                    for _, record, _ in ready:
                        record["download_concurrency"] = len(ready)
                    if len(ready) == 1:
                        model, _, manifest = ready[0]
                        engine.pull(model, manifest)
                        errors = [None]
                    else:
                        errors = engine.pull_many([(model, manifest) for model, _, manifest in ready])
                    downloaded = []
                    for (model, record, manifest), error in zip(ready, errors):
                        if error:
                            finish(model, record, "skipped", error)
                        else:
                            downloaded.append((model, record, manifest))
                    ready = downloaded
            except (BenchmarkError, OSError) as error:
                for model, record in active_group:
                    if record["status"] == "running":
                        finish(model, record, "skipped", str(error))
                ready = []
            finally:
                for _, record in active_group:
                    record["download_batch"] = {"model_tags": batch_tags, "elapsed_seconds": time.monotonic() - started,
                                                "resources": batch_guard.metrics()}
                reports.save()
            if not ready:
                with cleanup_signals():
                    engine.clear_model([], active_group[0][0]["ollama_tag"], False)
                continue
            store_ready = True
            for position, (model, record, manifest) in enumerate(ready):
                aliases = []
                current_storage = storage if store_ready else model
                guard = Guard(telemetry, model, policy, engine.paths, reports.directory, engine.store, commands.processes,
                              lambda sample: ui.update(sample=sample), storage_model=current_storage)
                commands.guard = guard
                try:
                    guard.admit(disk=not store_ready)
                    if not store_ready:
                        record["redownload_after_batch_failure"] = True
                        engine.start()
                        engine.pull(model, manifest)
                    elif position:
                        engine.start(expected_models=batch_tags)
                        engine.verify_download(model, manifest)
                    record["ollama_version"] = engine.version
                    record["downloads_during_inference"] = False
                    benchmark(engine, guard, model, record, catalog, ui, reports.save, aliases)
                    if not any(profile["metrics"].get("valid_generation_measurements", 0) for profile in record["profiles"]):
                        raise BenchmarkError("No usable generation timings were reported")
                    finish(model, record, "completed")
                except KeyboardInterrupt:
                    record.update(status="interrupted", skip_or_failure_reason="user_interrupt")
                    raise
                except (BenchmarkError, OSError) as error:
                    status = "failed" if record["probes"] or record["warmups"] or record["profiles"] else "skipped"
                    finish(model, record, status, str(error))
                finally:
                    record["metrics"] = guard.metrics()
                    preserve = record["status"] == "completed" and position < len(ready) - 1
                    ui.update(stage=f"{model['ollama_tag']} · cleanup")
                    with cleanup_signals():
                        if preserve:
                            engine.clear_model(aliases, model["ollama_tag"], True, preserve_store=True)
                        else:
                            engine.clear_model(aliases, model["ollama_tag"], record["status"] == "completed")
                    store_ready = preserve
                    reason = disk_reason(model, policy, engine.paths, admission=False)
                    if reason:
                        raise CleanupError("Disk reserve not restored after cleanup: " + reason)
                    reports.save()
        report["status"] = "completed"
    except KeyboardInterrupt:
        for _, record in [*active_group, *([deferred] if deferred else [])]:
            if record["status"] == "running":
                record.update(status="interrupted", skip_or_failure_reason="user_interrupt")
        raise
    finally:
        commands.guard = None
        with cleanup_signals():
            engine.stop_server()
            if workspace.is_symlink():
                raise CleanupError("Owned workspace became a symlink; refusing recursive deletion")
            shutil.rmtree(workspace)
