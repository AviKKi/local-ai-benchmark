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

The plan checks local RAM and disk without installing or downloading anything. The next command attempts the smallest eligible model and installs Ollama through Homebrew if needed. To benchmark every eligible model:

```sh
uv run local-ai-benchmark
```

With no arguments, an interactive terminal offers **resume** or **fresh** when compatible history exists. Resume keeps completed measurements for this hardware/OS and workload, while retrying skipped, failed and unfinished models. For explicit, non-interactive use:

```sh
uv run local-ai-benchmark --resume
uv run local-ai-benchmark --fresh
```

Reports and logs are written to `benchmarks/runs/<device-id>/<run-id>/`. Temporary aliases, installer cache and the owned server are cleaned up after each model; queued weights may remain until the pair finishes. The Ollama installation remains available. See [runner usage](architecture/runner-lifecycle.md#commands) for model filters, plain logs, publication and verification.

Downloads use **bounded pairs** by default, based on local network measurements. Only one model is loaded/benchmarked at a time, and no downloads run during timed inference. Queue disk admission includes both models and staging overhead; if the pair does not fit, the runner falls back to serial downloads. To force serial operation:

```sh
uv run local-ai-benchmark --resume --download-workers 1
```

## Latest Benchmarks

<!-- BENCHMARKS:START -->
Latest measurements: **mac16-11-64gib** · 17 models measured on **Apple M4 Pro**, 64 GiB RAM, macOS 26.5.1 · ollama version is 0.40.6.

The [latest run](benchmarks/runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) was interrupted; only completed model measurements are shown below. Earlier completed runs are in the [results index](benchmarks/README.md).

Sorted by single-request decode throughput, highest first.

| Model | Single decode tok/s | Sequential batch decode tok/s |
| --- | ---: | ---: |
| gemma3:270m-it-q8_0 | 309.24 | 326.86 |
| qwen3:0.6b-q4_K_M | 256.96 | 257.57 |
| llama3.2:1b-instruct-q4_K_M | 234.38 | 233.74 |
| gemma3:1b-it-q4_K_M | 175.90 | 176.93 |
| qwen2.5-coder:1.5b-instruct-q4_K_M | 169.59 | 169.29 |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | 169.25 | 168.41 |
| qwen3.5:0.8b-q8_0 | 158.25 | 159.18 |
| qwen3:1.7b-q4_K_M | 149.74 | 151.28 |
| qwen3.5:2b-q4_K_M | 119.51 | 118.05 |
| llama3.2:3b-instruct-q4_K_M | 99.75 | 99.44 |
| granite4.2:3b-q4_K_M | 88.21 | 88.16 |
| gemma4:e4b-it-q4_K_M | 84.73 | 84.55 |
| phi4-mini:3.8b-q4_K_M | 79.71 | 79.50 |
| granite4.2:8b-q4_K_M | 42.63 | 42.43 |
| qwen3.5:9b-q4_K_M | 39.44 | 39.27 |
| ministral-3:14b | 27.79 | 27.57 |
| deepseek-r1:14b-qwen-distill-q4_K_M | 26.39 | 26.17 |

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

