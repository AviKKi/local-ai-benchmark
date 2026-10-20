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

Reports and logs are written to `benchmarks/runs/<device-id>/<run-id>/`. Weights, temporary aliases, installer cache and the owned server are cleaned up after each model; the Ollama installation remains available. See [runner usage](architecture/runner-lifecycle.md#commands) for model filters, plain logs, publication and verification.

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

