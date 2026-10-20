# Benchmarking

This document defines comparable workloads, metrics and published reports. Settings and required result fields live in the `benchmark` section of [`models.json`](../models.json). Read [resource safety](resource-safety.md) before changing context size, batching or concurrency.

## Workload

The default workload fixes `num_ctx=2048`, `num_predict=256`, `num_batch=128`, temperature 0 and seed 42. The full rendered prompt, including the model's system/template tokens, must fit within 1,024 tokens. These limits take precedence over advertised 128K/256K/1M contexts, since [longer contexts consume more memory](https://docs.ollama.com/context-length). Unknown prompt tokenization must not result in an unbounded prompt.

There is one warmup, followed by a single-request profile and an eight-request **sequential** batch profile. Each request starts a fresh conversation while the same model remains resident. `num_batch` controls prompt-processing microbatch size; it does not mean 128 concurrent requests. [Parallel requests multiply context memory](https://docs.ollama.com/faq), so concurrent batch benchmarks require a separate admission budget and are outside these defaults.

Preserve and record each model's default thinking mode. Include generated thinking tokens when computing decoding throughput, and distinguish decoding tok/s from end-to-end throughput. Use CLI verbose timings where available, record missing metrics as null with a reason, and guard against zero durations. Record the installed Ollama version, resolved digest, actual context/backend/quantization, full host specs and observed resource peaks with each result. Seeds do not guarantee identical output across backends or versions.

## Metrics and Results

Measure prompt evaluation and generation throughput, wall time, model load time, CPU usage, GPU usage when available, peak memory, memory pressure and swap growth. Capture system specifications alongside both single-request and sequential-batch measurements. Preserve skip and failure reasons rather than omitting unsuccessful models.

Write machine-readable JSON and a human-readable Markdown report for each run:

```text
benchmarks/runs/<device-id>/<run-id>/
  results.json
  report.md
```

Use a stable, filesystem-safe device identifier and a unique UTC timestamp for the run ID, such as `2026-10-21T003000Z`. Keep detailed hardware specifications in the report rather than encoding them all in a directory name. These paths describe the intended output convention; no benchmark runs have been published yet.

## GitHub Publication

[`benchmarks/README.md`](../benchmarks/README.md) is the results landing page. A future report generator should update it with device/model comparisons and links to individual run reports.

The root [`README.md`](../README.md) contains one generated highlights section bounded by these exact markers:

```markdown
<!-- BENCHMARKS:START -->
Results coming soon.
<!-- BENCHMARKS:END -->
```

Replace only the content between the markers. Require exactly one opening and closing marker in the correct order, and leave the file untouched if validation fails. Use paths relative to the root README for highlight links. Derive highlights from saved run results and retain the surrounding manually maintained introduction and documentation links. The report generator is not implemented yet.


## Related Documentation

- [Runner lifecycle](runner-lifecycle.md)
- [Resource safety](resource-safety.md)
- [Roadmap and scope](roadmap.md)
