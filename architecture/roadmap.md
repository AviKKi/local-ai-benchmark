# Roadmap

The project starts with a small proof of concept, then expands to additional devices and model families. This document owns phase scope and planned capabilities.

## Phase 1: macOS and Ollama LLMs

Status: model catalog, modular Python runner, progress UI and JSON/Markdown reporting implemented. Initial live measurements are published for an Apple M4 Pro Mac mini with 64 GiB RAM; broader model and device coverage remains pending.

- Run on Apple Silicon macOS using the Ollama CLI.
- Benchmark text generation by local LLMs; test multimodal LLMs with text input only.
- Start with the Mac mini M4 with 64 GB RAM and MacBook Air M2 with 16 GB RAM.
- Detect system specifications, available RAM and free disk, then select models from [`models.json`](../models.json) using the [resource safety policy](resource-safety.md).
- Set up the inference engine when needed, download at most two admitted models in bounded pairs, and benchmark/unload one model at a time. Downloads finish before timed inference; queued weights are cleaned up by the end of each pair.
- Measure throughput and processing/memory usage for single inference and sequential batches.
- Produce JSON and Markdown reports, with a GitHub-friendly [results index](../benchmarks/README.md) and generated highlights in the root README.

MLX and other inference engines, concurrent request batches, non-macOS hosts, Intel Macs, speech, embeddings, decision-only models and image generation are outside Phase 1.

## Phase 2

Status: requirements gathering; additional requirements will be added later. Phase 1 execution and measurements remain unchanged.

### Requirement: Parallel Requests and Server Capacity

- Keep the single-request and sequential multi-request profiles as concurrency-one baselines.
- Test one resident model with explicit client and server concurrency levels, initially 1, 2, 4 and 8 simultaneous requests, admitting each level independently when resources permit.
- Budget additional per-request context/KV cache and runtime workspace before increasing concurrency; retain memory-pressure, swap, disk, timeout and owned-process cleanup safeguards.
- Verify that requests actually overlap in server execution rather than only accumulating in a queue. Distinguish synchronized request bursts from sustained concurrent-client load.
- Report aggregate generated tokens divided by workload elapsed wall time, completed requests per second, per-request decoding throughput, time to first token, p50/p95 latency, errors and peak resource usage.
- Use enough measured requests to characterize sustained serving performance, record workload size and settings, and identify throughput/latency tradeoffs rather than assuming linear scaling.
- Select and validate a request transport with concurrent execution and streaming timing support before implementation; do not assume the current serial CLI process runner supports these measurements.

## Future Scope

- Add friends' and family's devices for broader hardware comparisons.
- Support Windows, Linux and Android, including platform-specific setup and resource detection.
- Evaluate other inference engines, including MLX on supported Apple hardware.
- Add model families such as text-to-image, speech-to-text and text-to-speech with suitable workloads and metrics.

Future phases have no committed schedule. Define their resource controls and methodology before expanding the benchmark scope.


## Related Documentation

- [Runner lifecycle](runner-lifecycle.md)
- [Benchmark methodology](benchmarking.md)
- [Model catalog](model-catalog.md)
