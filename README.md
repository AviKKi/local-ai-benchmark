# Local AI Benchmark

Benchmark local AI models across everyday devices, with automatic model selection based on available memory and disk space. Each run will capture system specifications, inference speed and resource usage, with JSON results and Markdown reports for easy comparison.

Initial devices: **Mac mini M4 (64 GB RAM)** and **MacBook Air M2 (16 GB RAM)**. More devices will follow.

The Python runner measures Ollama throughput with coding, SQL and NER prompts, displays live progress, and records skipped models with their reasons. Measured results and source reports are published below.

## Run a Benchmark

Requires Apple Silicon macOS, [uv](https://docs.astral.sh/uv/getting-started/installation/) and Homebrew if Ollama is not installed. Run these commands from the repository root:

```sh
uv venv --python 3.13 --allow-existing
uv sync
uv run local-ai-benchmark --plan
uv run local-ai-benchmark --limit 1
```

The runner freezes its RAM cap at startup available memory (including reclaimable RAM) minus a 2 GiB buffer, and rechecks live RAM before each model and request. The plan checks local RAM and disk without installing or downloading anything. The next command attempts the smallest eligible model and installs Ollama through Homebrew if needed. To benchmark every eligible model:

```sh
uv run local-ai-benchmark --publish
```

`--publish` adds a successfully completed measured run to the results index and refreshes the generated highlights below. An interactive terminal offers **resume** or **fresh** when compatible history exists, including when options such as `--download-workers 1` are supplied. Pass `--resume` or `--fresh` to select a mode explicitly. Resume keeps completed measurements for this hardware/OS and workload, while retrying skipped, failed and unfinished models. For explicit, non-interactive use:

```sh
uv run local-ai-benchmark --resume
uv run local-ai-benchmark --fresh
```

To regenerate the published README highlights and results index from saved reports without running a benchmark:

```sh
uv run local-ai-benchmark --publish-only
```

Reports and logs are written to `benchmarks/runs/<device-id>/<run-id>/`. Temporary aliases, installer cache and the owned server are cleaned up after each model; queued weights may remain until the pair finishes. The Ollama installation remains available. See [runner usage](architecture/runner-lifecycle.md#commands) for model filters, plain logs, publication and verification.

Downloads use **bounded pairs** by default, based on local network measurements. Only one model is loaded/benchmarked at a time, and no downloads run during timed inference. Queue disk admission includes both models and staging overhead; if the pair does not fit, the runner falls back to serial downloads. To force serial operation:

```sh
uv run local-ai-benchmark --resume --download-workers 1
```

## Latest Benchmarks

<!-- BENCHMARKS:START -->
Latest completed measurement for each model from saved runs.

| Model | Device | Single decode tok/s | Sequential batch decode tok/s | Source |
| --- | --- | ---: | ---: | --- |
| gemma3:270m-it-q8_0 | mac16-11-64gib | 309.24 | 326.86 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| qwen3:0.6b-q4_K_M | mac16-11-64gib | 256.96 | 257.57 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| llama3.2:1b-instruct-q4_K_M | mac16-11-64gib | 234.38 | 233.74 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| gemma3:1b-it-q4_K_M | mac16-11-64gib | 175.90 | 176.93 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| qwen2.5-coder:1.5b-instruct-q4_K_M | mac16-11-64gib | 169.59 | 169.29 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | mac16-11-64gib | 169.25 | 168.41 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| qwen3.5:0.8b-q8_0 | mac16-11-64gib | 158.25 | 159.18 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| lfm2.5:8b-a1b-q4_K_M | mac16-11-64gib | 151.85 | 151.88 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3:1.7b-q4_K_M | mac16-11-64gib | 149.74 | 151.28 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| gemma4:e2b-it-q4_K_M | mac16-11-64gib | 123.37 | 135.62 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3.5:2b-q4_K_M | mac16-11-64gib | 119.51 | 118.05 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| lfm2.5:24b-a2b-q4_K_M | mac16-11-64gib | 101.09 | 101.32 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| llama3.2:3b-instruct-q4_K_M | mac16-11-64gib | 99.75 | 99.44 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| granite4.2:3b-q4_K_M | mac16-11-64gib | 88.21 | 88.16 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| ministral-3:3b-instruct-2512-q4_K_M | mac16-11-64gib | 84.80 | 84.57 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| gemma4:e4b-it-q4_K_M | mac16-11-64gib | 84.73 | 84.55 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| phi4-mini:3.8b-q4_K_M | mac16-11-64gib | 79.71 | 79.50 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| north-mini-code-1.0:q4_K_M | mac16-11-64gib | 76.64 | 76.59 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| gemma4:26b-a4b-it-q4_K_M | mac16-11-64gib | 63.20 | 63.30 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3.5:4b-q4_K_M | mac16-11-64gib | 59.73 | 60.51 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| gpt-oss:20b | mac16-11-64gib | 55.24 | 55.23 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| glm-4.7-flash:q4_K_M | mac16-11-64gib | 55.21 | 54.43 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen2.5-coder:7b-instruct-q4_K_M | mac16-11-64gib | 50.80 | 50.77 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| gemma4:12b-it-q4_K_M | mac16-11-64gib | 49.41 | 49.26 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3:8b-q4_K_M | mac16-11-64gib | 45.19 | 44.85 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| ministral-3:8b-instruct-2512-q4_K_M | mac16-11-64gib | 42.83 | 42.62 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| granite4.2:8b-q4_K_M | mac16-11-64gib | 42.63 | 42.43 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| ornith-1.5:9b | mac16-11-64gib | 39.89 | 39.73 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3.5:9b-q4_K_M | mac16-11-64gib | 39.44 | 39.27 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| ministral-3:14b | mac16-11-64gib | 27.79 | 27.57 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| deepseek-r1:14b-qwen-distill-q4_K_M | mac16-11-64gib | 26.39 | 26.17 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) |
| qwen3:14b-q4_K_M | mac16-11-64gib | 26.16 | 25.98 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| phi4:14b-q4_K_M | mac16-11-64gib | 25.41 | 25.10 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| mistral-small3.2:24b | mac16-11-64gib | 17.01 | 16.83 | [report](benchmarks/runs/mac16-11-64gib/2026-10-21T191107.035609Z/report.md) |
| devstral-small-2:24b-instruct-2512-q4_K_M | mac16-11-64gib | 16.62 | 16.47 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| qwen3.6:27b-q4_K_M | mac16-11-64gib | 13.89 | 13.78 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| granite4.2:30b-q4_K_M | mac16-11-64gib | 13.43 | 13.26 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| olmo-3.1:32b-instruct-q4_K_M | mac16-11-64gib | 12.39 | 12.26 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |
| olmo-3.1:32b-think-q4_K_M | mac16-11-64gib | 12.37 | 12.24 | [report](benchmarks/runs/mac16-11-64gib/2026-10-21T191107.035609Z/report.md) |
| deepseek-r1:32b-qwen-distill-q4_K_M | mac16-11-64gib | 12.18 | 12.05 | [report](benchmarks/runs/mac16-11-64gib/2026-10-21T191107.035609Z/report.md) |
| qwen3:32b | mac16-11-64gib | 11.93 | 11.79 | [report](benchmarks/runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) |

Decode throughput includes generated thinking tokens where reported. Requests run sequentially; probes and warmups are excluded. Output quality is not scored.
<!-- BENCHMARKS:END -->

[View all benchmark results](benchmarks/README.md)

## Documentation

- [Roadmap and phase scope](architecture/roadmap.md)
- [Model catalog and metadata](architecture/model-catalog.md) · [models.json](models.json)
- [Resource safety and model admission](architecture/resource-safety.md)
- [Runner setup, execution and cleanup](architecture/runner-lifecycle.md)
- [Benchmark methodology and result publication](architecture/benchmarking.md)

For model selection changes, read the model catalog and resource safety documents. For runner changes, also read the lifecycle and benchmarking documents.
