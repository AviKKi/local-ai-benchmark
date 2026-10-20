# Local AI Benchmark

Benchmark local AI models across everyday devices, with automatic model selection based on available memory and disk space. Each run will capture system specifications, inference speed and resource usage, with JSON results and Markdown reports for easy comparison.

Initial devices: **Mac mini M4 (64 GB RAM)** and **MacBook Air M2 (16 GB RAM)**. More devices will follow.

The Python runner measures Ollama throughput with coding, SQL and NER prompts, displays live progress, and records skipped models with their reasons. No measured results have been published yet.

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

A separate [partial-download experiment](architecture/runner-lifecycle.md#download-concurrency-experiment) compares serial and parallel network transfers without changing benchmark execution or loading models.

## Latest Benchmarks

<!-- BENCHMARKS:START -->
Results coming soon.
<!-- BENCHMARKS:END -->

[View all benchmark results](benchmarks/README.md)

## Documentation

- [Roadmap and phase scope](architecture/roadmap.md)
- [Model catalog and metadata](architecture/model-catalog.md) · [models.json](models.json)
- [Resource safety and model admission](architecture/resource-safety.md)
- [Runner setup, execution and cleanup](architecture/runner-lifecycle.md)
- [Benchmark methodology and result publication](architecture/benchmarking.md)

For model selection changes, read the model catalog and resource safety documents. For runner changes, also read the lifecycle and benchmarking documents.

