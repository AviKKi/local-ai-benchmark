# Benchmarking

This document defines comparable workloads, metrics and published reports. Settings and required result fields live in the `benchmark` section of [`models.json`](../models.json). Read [resource safety](resource-safety.md) before changing context size, batching or concurrency.

## Workload

The default workload fixes `num_ctx=2048`, `num_predict=256`, `num_batch=128`, temperature 0 and seed 42. The full rendered prompt, including the model's system/template tokens, must fit within 1,024 tokens. These limits take precedence over advertised 128K/256K/1M contexts, since [longer contexts consume more memory](https://docs.ollama.com/context-length). Unknown prompt tokenization must not result in an unbounded prompt.

[`prompts.py`](../src/local_bench/prompts.py) supplies three short ASCII workloads: Python merge sort, a SQL top-orders query, and named-entity extraction. Each input is capped at 256 bytes. Output quality and exact problem wording are not evaluated. Before measured inference, the runner creates a separate alias with `num_predict=1` and probes every prompt, retaining the native system/template. The fixed 2048-token context bounds those probes; a missing or oversized rendered prompt count causes a skip before any measured requests. Probe metrics are retained separately, then the probe alias is unloaded before the benchmark alias is warmed up.

There is one warmup, followed by a single-request profile and an eight-request **sequential** batch profile. Each request starts a fresh conversation while the same model remains resident. `num_batch` controls prompt-processing microbatch size; it does not mean 128 concurrent requests. [Parallel requests multiply context memory](https://docs.ollama.com/faq), so concurrent batch benchmarks require a separate admission budget and are outside these defaults.

Preserve and record each model's default thinking mode. Include generated thinking tokens when computing decoding throughput, and distinguish decoding tok/s from end-to-end throughput. Use CLI verbose timings where available, record missing metrics as null with a reason, and guard against zero durations. Record the installed Ollama version, resolved digest, actual context/backend/quantization, full host specs and observed resource peaks with each result. Seeds do not guarantee identical output across backends or versions.

No thinking flag is passed: results explicitly record the model default and that the CLI does not expose the effective reasoning effort. Generation counts come from Ollama's verbose output rather than re-tokenizing displayed text. Profile decoding throughput is the sum of valid generated tokens divided by the sum of their generation durations; it is not an unweighted average of per-request rates. End-to-end throughput includes command wall time. Native prompt caches may be warm between fresh conversations; cached prompt tokens are recorded when the installed CLI exposes them.

## Metrics and Results

Measure prompt evaluation and generation throughput, wall time, model load time, CPU usage, GPU usage when available, peak memory, memory pressure and swap growth. Capture system specifications alongside both single-request and sequential-batch measurements. Preserve skip and failure reasons rather than omitting unsuccessful models.

Write machine-readable JSON and a human-readable Markdown report for each run:

```text
benchmarks/runs/<device-id>/<run-id>/
  results.json
  report.md
```

Use a stable, filesystem-safe device identifier and a unique UTC timestamp for the run ID, such as `2026-10-21T003000.123456Z`. Keep detailed hardware specifications in the report rather than encoding them all in a directory name. The runner also writes `events.jsonl` and a bounded `ollama.log`. Plan-only and interrupted runs are labelled explicitly and cannot be published as completed measurements.

## GitHub Publication

[`benchmarks/README.md`](../benchmarks/README.md) is the results landing page. Pass `--publish` to add a link to a completed measured run and update root README highlights.

The root [`README.md`](../README.md) contains one generated highlights section bounded by these exact markers:

```markdown
<!-- BENCHMARKS:START -->
Results coming soon.
<!-- BENCHMARKS:END -->
```

Replace only the content between the markers. Require exactly one opening and closing marker in the correct order, and leave the file untouched if validation fails. Use paths relative to the root README for highlight links. Derive highlights from saved run results and retain the surrounding manually maintained introduction and documentation links. Publication requires at least one completed model; plan-only reports do not qualify.


## Related Documentation

- [Runner lifecycle](runner-lifecycle.md)
- [Resource safety](resource-safety.md)
- [Roadmap and scope](roadmap.md)
