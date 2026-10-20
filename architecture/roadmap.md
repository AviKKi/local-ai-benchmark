# Roadmap

The project starts with a small proof of concept, then expands to additional devices and model families. This document owns phase scope and planned capabilities.

## Phase 1: macOS and Ollama LLMs

Status: model catalog, modular Python runner, progress UI and JSON/Markdown reporting implemented. Live model validation and published measurements are pending.

- Run on Apple Silicon macOS using the Ollama CLI.
- Benchmark text generation by local LLMs; test multimodal LLMs with text input only.
- Start with the Mac mini M4 with 64 GB RAM and MacBook Air M2 with 16 GB RAM.
- Detect system specifications, available RAM and free disk, then select models from [`models.json`](../models.json) using the [resource safety policy](resource-safety.md).
- Set up the inference engine when needed, download at most two admitted models in bounded pairs, and benchmark/unload one model at a time. Downloads finish before timed inference; queued weights are cleaned up by the end of each pair.
- Measure throughput and processing/memory usage for single inference and sequential batches.
- Produce JSON and Markdown reports, with a GitHub-friendly [results index](../benchmarks/README.md) and generated highlights in the root README.

MLX and other inference engines, concurrent request batches, non-macOS hosts, Intel Macs, speech, embeddings, decision-only models and image generation are outside Phase 1.

## Future Scope

- Add friends' and family's devices for broader hardware comparisons.
- Support Windows, Linux and Android, including platform-specific setup and resource detection.
- Evaluate other inference engines, including MLX on supported Apple hardware.
- Add model families such as text-to-image, speech-to-text and text-to-speech with suitable workloads and metrics.
- Add concurrent batching with explicit memory budgets and clearly distinguished throughput measurements.

Future phases have no committed schedule. Define their resource controls and methodology before expanding the benchmark scope.


## Related Documentation

- [Runner lifecycle](runner-lifecycle.md)
- [Benchmark methodology](benchmarking.md)
- [Model catalog](model-catalog.md)
