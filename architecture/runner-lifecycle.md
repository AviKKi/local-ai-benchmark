# Runner Lifecycle

This document describes how the Python runner sets up Ollama, processes models and cleans up. CLI argument templates, environment variables, timeouts and teardown rules live in [`models.json`](../models.json). Run commands from the repository root.

## Commands

```sh
uv venv --python 3.13 --allow-existing
uv sync
uv run local-ai-benchmark --plan
uv run local-ai-benchmark --limit 1
uv run local-ai-benchmark
```

`--plan` performs only local capacity checks. It creates a report but never installs Ollama, contacts the registry or downloads weights. An eligible plan entry still needs manifest verification and a successful live backend check.

To select models, change the output location or use plain progress logs:

```sh
uv run local-ai-benchmark --model 'qwen3.5:*' --limit 2
uv run local-ai-benchmark --model gemma3:270m-it-q8_0 --no-ui
uv run local-ai-benchmark --device m2-air-16gb --output-dir benchmarks/runs
uv run local-ai-benchmark --models-file models.json --work-dir /Volumes/Bench/.benchmark-work
```

Quote glob patterns so the shell does not expand them. `--limit` caps statically eligible attempts, including attempts later rejected by registry or backend checks. Disabled, incompatible and capacity-rejected models have explicit skip reasons. The Rich terminal dashboard shows model counts, the current stage, download layer progress, available memory, owned process footprint, throughput and recent events. Non-interactive terminals automatically use plain logs.

### Download Scheduling

The catalog now defaults to **two concurrent downloads**, never more than two queued models. Both pulls finish before any inference begins. The runner then benchmarks the pair serially with one loaded model and no background transfers during measurements. This is a network optimization, not Phase 2 concurrent inference or download/compute overlap.

```sh
uv run local-ai-benchmark --resume
uv run local-ai-benchmark --resume --download-workers 1
uv run local-ai-benchmark --resume --download-workers 2
```

Two user-run partial-transfer sweeps measured single-download throughput of 9.868/9.486 MB/s and two-download aggregate throughput of 11.390/10.965 MB/s, about 15–16% higher. Four/six downloads gave only modest additional bandwidth; two stayed within 5% of peak in both sweeps. This selects a conservative default, not a claim that full model downloads or every network will see the same gain.

Only statically eligible, non-reused models within `--limit` enter the pair queue. Combined disk admission reserves all queued weights plus staging; insufficient pair capacity causes automatic serial fallback. Each artifact retains independent manifest/blob verification, skip/failure handling and load-time admission checks. Partial pair failures still allow a verified partner to benchmark. Failure during inference clears the cache and safely re-downloads a later partner if needed.

Reports record the requested download worker count, strategy, batch membership, batch resource peaks/elapsed preparation time and actual download concurrency per model. Batch preparation time includes metadata/startup, not just network transfer. Inference resource metrics have a separate baseline after downloads complete. `--download-workers 1` retains the original serial lifecycle; `--plan` remains local-only and never launches concurrent work.

### Resume or Fresh

The runner offers resume or fresh if compatible history exists and stdin is a terminal, including with options such as `--download-workers 1`, `--model` or `--publish`. Enter accepts resume. With no compatible history it starts fresh. If history exists but stdin is not interactive, pass an explicit mode rather than relying on a prompt:

```sh
uv run local-ai-benchmark --resume
uv run local-ai-benchmark --fresh
uv run local-ai-benchmark --resume --model 'qwen3.5:*' --no-ui
```

Explicit `--resume` and `--fresh` bypass the prompt, as do `--plan` and `--publish-only`. For backward compatibility, non-interactive invocations with other explicit options retain fresh-run behavior unless `--resume` is passed; scripts should always specify their intended mode. `--resume` cannot be combined with `--fresh` or `--plan`.

Resume scans the output directory's compatible run history, not just the last report: a newer interrupted or limited run cannot hide older successes. Compatibility matches hardware configuration, physical RAM, architecture and OS version (not volatile available memory), benchmark settings and prompts. No serial number or hardware UUID is used, so identically configured machines sharing a results directory cannot be uniquely distinguished. Use separate output directories for such machines. Changing `--device` only changes the new report label; it does not discard matching history.

Only completed model records with all expected measured requests, usable timing metrics, matching context/quantization and a manifest digest matching the current catalog prefix are reusable. Failed, skipped, interrupted, missing or incomplete models are attempted again subject to current safety checks. A resource-constrained model may consequently be skipped again. Old reports remain untouched; each resume creates a new report containing reused results with their original run provenance and model-specific Ollama version. `REUSED` events and the dashboard distinguish these from new completions and actual skips. Reused models do not consume `--limit` attempts.

History from before measurement signatures were introduced is checked against recorded options, prompts and complete profiles. New reports additionally fingerprint the full benchmark configuration. Resume is not an engine-version comparison: preserved results may come from an earlier Ollama version. Use `--fresh` to remeasure after engine changes or to obtain an entirely new snapshot.

Publish highlights and add a link to the results index after a measured run:

```sh
uv run local-ai-benchmark --limit 1 --publish
```

Publication requires at least one successfully measured model and output under this project's `benchmarks/runs/`. It preserves content outside the root README markers and does not push or commit changes.

Regenerate publication from the saved archive without initializing telemetry, acquiring the run lock, downloading a model or invoking Ollama:

```sh
uv run local-ai-benchmark --publish-only
```

Run the tests without downloading models:

```sh
uv run python -m unittest discover -s tests -v
```

The runner requires Python 3.11 or later. `uv sync` installs the package, its CLI entry point, Rich and psutil; uv can obtain Python 3.13 if it is missing. Homebrew must already be available for automatic `brew install ollama`; otherwise install Ollama manually. The runner never launches Homebrew's Ollama service or reuses the desktop daemon. An installed Ollama must advertise the required isolation and resource settings, including cloud disablement.

## Modules

| Module | Responsibility |
| --- | --- |
| `src/local_bench/cli.py` | Selection, exclusive run lock, orchestration, interruption and exit status |
| `src/local_bench/history.py` | Compatible historical measurements, resume selection and result provenance |
| `src/local_bench/downloads.py` | Bounded download pairs, combined disk admission, serial fallback and queued artifact lifecycle |
| `src/local_bench/config.py` | Catalog validation and fixed Modelfile settings |
| `src/local_bench/system.py` | macOS pressure, available RAM, swap and owned physical footprints |
| `src/local_bench/safety.py` | Memory/disk admission and watchdog |
| `src/local_bench/processes.py` | Bounded output, timeouts and owned process-group termination |
| `src/local_bench/registry.py` | Frozen manifest/config verification and layer accounting |
| `src/local_bench/metadata_worker.py` | Killable metadata HTTP/DNS work under the same watchdog |
| `src/local_bench/engine.py` | Ollama install, environment verification, aliases, CLI runs and teardown |
| `src/local_bench/prompts.py`, `src/local_bench/metrics.py` | Workloads, CLI timings and aggregation |
| `src/local_bench/ui.py`, `src/local_bench/reports.py` | Live display, checkpoints, logs and publication |

## Execution Order

1. Read and validate the catalog, check the host, and apply [resource admission checks](resource-safety.md) before installing or downloading anything.

2. Take an exclusive run lock and use a fresh, run-owned model store plus an owned `ollama serve` process on the configured loopback port. Refuse an occupied port. Verify the daemon received the configured environment and uses the intended store. Merely setting variables on an `ollama run` client does not configure an already-running server. Check `ollama serve --help` and model/backend support for the installed version; unsupported options or formats must produce a skip.

3. Resolve and verify the manifest, check disk capacity, and install Ollama if needed. Recheck resources after installation and before pulling. Follow [resource safety](resource-safety.md) for the complete rules.

4. With the default two-download policy, admit and pull at most two models together; fall back to one if combined disk admission fails. Verify each local artifact against its resolved manifest. Only after all pulls finish, create a run-owned alias for one model from `engine.modelfile_template` so the CLI uses the pinned context, output and prompt-processing limits. Admit its smoke load under the same memory budget. Check actual context/backend/quantization and recheck resources before each request. The serial override pulls and measures one model at a time.

5. Validate all three prompts with a one-token probe alias under the fixed context limit, then unload that alias and run the [benchmark profiles](benchmarking.md). Check resources before every request and run the watchdog throughout setup, download, load and inference. On a timeout or watchdog trigger, stop only the owned server and wait for exit before cleanup or recovery.

6. After each model, unload it, remove the temporary alias and source tag, and verify unload and free space before proceeding. Handle success, failure and interruption. Failed pulls may leave partial blobs: remove them only inside the exclusive run-owned store after stopping its server. Never remove preexisting user models or assume `ollama rm` reclaimed shared blobs. An unload/cleanup failure stops the run. Shut down the owned server during final teardown.

## Ownership and Recovery

Use argument arrays directly instead of shell-interpolated commands. Keep temporary aliases, files, downloads and the daemon associated with one run. Handle interruption with the same cleanup rules as other failures.

Record each model as successful, skipped or failed, with a reason when applicable. Restart the owned server after an abort only when cleanup succeeds and live health checks pass. Stop the entire run on an unload or cleanup failure.

`results.json` and `report.md` are checkpointed during execution. `events.jsonl` records commands, progress and skip/failure reasons; `ollama.log` captures bounded server output. Generation text is captured only within the command byte limit for execution and then discarded. No serial numbers or hardware UUIDs are collected.

The isolated store lives in a unique directory under `.benchmark-work/` by default. Each model is unloaded and the owned server is stopped after measurement. In paired mode, the store may retain the verified queued partner across the next server restart on port 11435; only expected queued model names are accepted. The pair's store is emptied before another pair starts. An occupied port causes a skip. Homebrew's cache and temporary files are directed into the run workspace. Installation destination capacity is checked separately, including when the workspace is on another volume. Ollama itself remains installed after the run.

Ctrl-C and SIGTERM trigger teardown; exit code 130 indicates interruption. Fatal setup, telemetry or cleanup failures return a nonzero exit code. Individual model skips/failures are recorded while processing continues. SIGKILL, power loss and a machine crash cannot run Python cleanup handlers: a stale run directory may remain, and an occupied port is never resolved by killing an unrelated process. Inspect the saved logs and the process ownership before manually removing stale files.


## Related Documentation

- [Resource safety](resource-safety.md)
- [Model catalog](model-catalog.md)
- [Benchmark methodology](benchmarking.md)
