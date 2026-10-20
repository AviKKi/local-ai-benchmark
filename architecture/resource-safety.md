# Resource Safety

This document defines admission checks and monitoring for downloads and inference. Numeric configuration in [`models.json`](../models.json) is authoritative; the formulas below explain its current policy. Read this document when changing model selection, resource budgets or failure handling.

RAM estimates are unmeasured planning values. A catalog cannot prevent OOM by itself, and monitoring cannot guarantee protection against allocation spikes or competing applications. A future runner must enforce these rules and skip work when required telemetry is unavailable.

## Admission Checks

1. Validate the configuration, supported schema version, finite positive capacities, unique IDs/tags and supported host. Skip disabled entries. Obtain live physical RAM, conservatively available RAM, memory pressure, swap usage and actual free disk. Missing required telemetry means skip, not unlimited capacity. On macOS, use page-size-aware VM statistics and memory pressure; do not treat total RAM, compressed pages, swap or all cached pages as freely available capacity. Never add GPU memory to physical RAM on Apple Silicon.

2. Apply the memory formula in `policy.memory` **before downloading** and again immediately before loading. With `peak` from the model, compute `budget = ceil(peak * 1.25)`. Require the model's physical-memory minimum, `budget <= physical * 0.60`, `budget + 4 GiB <= physical`, normal memory pressure, and `budget + 2 GiB <= available`. If Metal reports a recommended working set, additionally require `budget <= recommended_working_set * 0.80`. These constraints use unified memory once. No swap-backed admission or automatic CPU fallback.

3. Fetch the HTTPS manifest as bounded metadata, verify the observed digest prefix, and record its full SHA-256. Reject indexes/MLX/cloud/non-GGUF artifacts instead of selecting a different backend. Check every layer and config size, including projectors or draft weights. Sum their bytes without shared-blob deductions. Reject an oversized, changed, missing or malformed manifest; do not silently update the catalog or pull first to discover its size.

4. Check the actual volumes backing the model store, temporary directory, results and installer cache. Reserve three times the model's download upper bound on the model-store volume, 2 GiB for installation and 1 GiB for results on their respective volumes. The three-times allowance covers final weights plus download/staging overhead; reserve an additional full upper bound on a separate temporary volume if it is used for model staging. Aggregate charges when paths share a volume. After these charges, each volume must retain `max(20 GiB, 10% of volume capacity)`. Use actual free space, excluding speculative purgeable space. Install only after this check, then recheck before pulling. Never download the entire catalog in advance.

## Runtime Watchdog

Run the watchdog during installation, download, load, warmup and inference, using the configured polling interval, memory budget, memory-pressure, swap-growth, disk and output limits. Measure the server **and model runner**, not only the small CLI client; include Metal allocations without double-counting shared pages. Take a swap baseline before each stage. If a bound or timeout is reached, cancel clients and stop the owned daemon, waiting for exit so server-side inference/downloads actually stop. A disconnected CLI is not proof that server work ended. Never kill an unrelated daemon. Record the failure, clean up, and continue only after the host is healthy and the owned server is restarted.

Record rejected models and their reasons in both JSON and Markdown output. Static eligibility does not establish that a model can complete a benchmark. Apply these checks before downloading, loading and each request, as configured by `policy`.


## Related Documentation

- [Model catalog](model-catalog.md)
- [Runner lifecycle](runner-lifecycle.md)
- [Benchmark methodology](benchmarking.md)
