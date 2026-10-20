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

Publish highlights and add a link to the results index after a measured run:

```sh
uv run local-ai-benchmark --limit 1 --publish
```

Publication requires at least one successfully measured model and output under this project's `benchmarks/runs/`. It preserves content outside the root README markers and does not push or commit changes.

Run the tests without downloading models:

```sh
uv run python -m unittest discover -s tests -v
```

The runner requires Python 3.11 or later. `uv sync` installs the package, its CLI entry point, Rich and psutil; uv can obtain Python 3.13 if it is missing. Homebrew must already be available for automatic `brew install ollama`; otherwise install Ollama manually. The runner never launches Homebrew's Ollama service or reuses the desktop daemon. An installed Ollama must advertise the required isolation and resource settings, including cloud disablement.

## Modules

| Module | Responsibility |
| --- | --- |
| `src/local_bench/cli.py` | Selection, exclusive run lock, orchestration, interruption and exit status |
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

4. Pull one model and verify the local digest against the resolved manifest. Create a run-owned alias from `engine.modelfile_template` so the CLI uses the pinned context, output and prompt-processing limits. Admit its smoke load under the same memory budget. Check actual context and backend with `ollama ps`; skip CPU/mixed offload or mismatched settings. Record actual quantization and reasoning behavior. Recheck resource availability before each request.

5. Validate all three prompts with a one-token probe alias under the fixed context limit, then unload that alias and run the [benchmark profiles](benchmarking.md). Check resources before every request and run the watchdog throughout setup, download, load and inference. On a timeout or watchdog trigger, stop only the owned server and wait for exit before cleanup or recovery.

6. After each model, unload it, remove the temporary alias and source tag, and verify unload and free space before proceeding. Handle success, failure and interruption. Failed pulls may leave partial blobs: remove them only inside the exclusive run-owned store after stopping its server. Never remove preexisting user models or assume `ollama rm` reclaimed shared blobs. An unload/cleanup failure stops the run. Shut down the owned server during final teardown.

## Ownership and Recovery

Use argument arrays directly instead of shell-interpolated commands. Keep temporary aliases, files, downloads and the daemon associated with one run. Handle interruption with the same cleanup rules as other failures.

Record each model as successful, skipped or failed, with a reason when applicable. Restart the owned server after an abort only when cleanup succeeds and live health checks pass. Stop the entire run on an unload or cleanup failure.

`results.json` and `report.md` are checkpointed during execution. `events.jsonl` records commands, progress and skip/failure reasons; `ollama.log` captures bounded server output. Generation text is captured only within the command byte limit for execution and then discarded. No serial numbers or hardware UUIDs are collected.

The isolated store lives in a unique directory under `.benchmark-work/` by default. Each model starts a fresh owned server on port 11435; an occupied port causes a skip. Homebrew's cache and temporary files are directed into the run workspace. Installation destination capacity is checked separately, including when the workspace is on another volume. Ollama itself remains installed after the run.

Ctrl-C and SIGTERM trigger teardown; exit code 130 indicates interruption. Fatal setup, telemetry or cleanup failures return a nonzero exit code. Individual model skips/failures are recorded while processing continues. SIGKILL, power loss and a machine crash cannot run Python cleanup handlers: a stale run directory may remain, and an occupied port is never resolved by killing an unrelated process. Inspect the saved logs and the process ownership before manually removing stale files.


## Related Documentation

- [Resource safety](resource-safety.md)
- [Model catalog](model-catalog.md)
- [Benchmark methodology](benchmarking.md)
