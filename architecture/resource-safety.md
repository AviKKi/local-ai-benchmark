# Resource Safety

This document defines admission checks and monitoring for downloads and inference. Numeric configuration in [`models.json`](../models.json) is authoritative; the formulas below explain its current policy. Read this document when changing model selection, resource budgets or failure handling.

RAM estimates are unmeasured planning values. A catalog cannot prevent OOM by itself, and monitoring cannot guarantee protection against allocation spikes or competing applications. The runner enforces these rules and skips work when required telemetry is unavailable. Run it in a normal terminal: restricted sandboxes may block macOS pressure or process telemetry and will cause a safe abort.

## Admission Checks

1. Validate the configuration, supported schema version, finite positive capacities, unique IDs/tags and supported host. Skip disabled entries. Obtain physical RAM, available RAM including reclaimable memory, memory pressure, swap usage and actual free disk. Missing required telemetry means skip, not unlimited capacity. On macOS, use `psutil.virtual_memory().available` directly: it already includes reclaimable memory, so never add free/inactive/cached pages to it again. Do not count swap or GPU memory as extra capacity.

2. Capture available RAM once during startup, before the resume prompt or any downloads, and freeze `cap = max(0, startup_available - 2 GiB)` for the entire run. Print it and record startup available RAM, buffer and cap in JSON and Markdown reports. Reclaimed memory later in the run cannot raise this ceiling. The former 60% physical-memory cap, additional OS reserve, fixed minimum-host-tier filter and Metal-fraction cap no longer apply. `minimum_physical_memory_bytes` remains advisory catalog metadata.

   With `peak` from the model, compute `budget = ceil(peak * 1.25)`. Before downloading, loading and each request require `budget <= cap`, normal memory pressure, and `budget + 2 GiB <= current_available`. Before a request on an already resident run-owned model, the live test uses `max(0, budget - verified_owned_physical_footprint) + 2 GiB`, avoiding charging its existing allocation twice. Resident credit never relaxes the startup cap. No swap-backed admission or automatic CPU fallback. Runtime monitoring enforces the smaller of the model budget and frozen startup cap, retains the 2 GiB available-memory floor, and still aborts on pressure or swap growth.

3. Fetch the HTTPS manifest as bounded metadata, verify the observed digest prefix, and record its full SHA-256. Reject indexes/MLX/cloud/non-GGUF artifacts instead of selecting a different backend. Check every layer and config size, including projectors or draft weights. Manifests and config responses have a 16 MiB metadata cap. Verify config bytes against their SHA-256 even if the manifest declares an inaccurate config size; record the discrepancy and reserve the larger of declared and verified sizes. Model layer sizes remain strict. Sum their bytes without shared-blob deductions. Reject an oversized, changed, missing or malformed manifest; do not silently update the catalog or pull first to discover its size.

4. Check the actual volumes backing the model store, temporary directory, results and installer cache. Reserve three times the model's download upper bound on the model-store volume, 2 GiB for installation and 1 GiB for results on their respective volumes. The three-times allowance covers final weights plus download/staging overhead; reserve an additional full upper bound on a separate temporary volume if it is used for model staging. Aggregate charges when paths share a volume. After these charges, each volume must retain `max(20 GiB, 10% of volume capacity)`. Use actual free space, excluding speculative purgeable space. Install only after this check, then recheck before pulling. Never download the entire catalog in advance.

   The implementation additionally reserves the installer budget at Homebrew's installation destination. This protects the boot volume when cache/work directories are on another disk and is conservative when both locations share a volume.

## Bounded Download Pairs

The default download limit is two, with one loaded model and one inference request at a time. Resolve each manifest before pulling. Before admitting a pair, use the **sum** of both catalog download upper bounds in the disk formula, with no shared-blob deductions. This includes both retained and queued weights, temporary staging, installer/results budgets and the existing `max(20 GiB, 10%)` reserve, which is stricter than a 10 GiB floor. If individual models fit but the pair does not, defer the second model and download serially instead of skipping it solely for pair capacity.

During paired transfers, both CLI clients and the owned daemon are included in the watchdog. No model is loaded; the largest individually admitted model's memory budget bounds the download phase rather than reserving two loaded models. During inference, use the current model's memory budget while retaining the combined store-size bound for any queued weights. Recheck RAM before each load/request and disk reserves throughout. All pulls finish before probes, warmup or timed inference begin, so CPU/disk/network activity from downloads cannot overlap measured inference.

After successful inference, remove that model's aliases/source and stop the daemon. Preserve only the owned store for the already-downloaded partner; a restarted daemon must list no unexpected model names, and the queued artifact is reverified before use. Clear the entire store/cache/temp directories at the end of the pair. A failed inference invalidates the pair cache and clears all owned weights; a later partner is re-downloaded safely instead of using potentially stale files. A failed pull does not discard a successfully verified partner. A watchdog/timeout abort terminates both clients and the daemon before cleanup.

## Runtime Watchdog

Run the watchdog during installation, download, load, warmup and inference, using the configured polling interval, memory budget, memory-pressure, swap-growth, disk and output limits. Measure the server **and model runner**, not only the small CLI client; include Metal allocations without double-counting shared pages. Take a swap baseline before each stage. If a bound or timeout is reached, cancel clients and stop the owned daemon, waiting for exit so server-side inference/downloads actually stop. A disconnected CLI is not proof that server work ended. Never kill an unrelated daemon. Record the failure, clean up, and continue only after the host is healthy and the owned server is restarted.

Record rejected models and their reasons in both JSON and Markdown output. Static eligibility does not establish that a model can complete a benchmark. Apply these checks before downloading, loading and each request, as configured by `policy`.

The memory watchdog uses macOS process physical-footprint accounting for the owned server, runners and active command. It separately tracks the drop in system available memory since the model began and compares the larger value to the model budget; it does not add CPU and GPU memory estimates together. Shared/kernel attribution and activity in other applications can affect these observations, so they are conservative operational measurements rather than exact GPU memory attribution. GPU utilization is reported as null with an explicit reason because it requires additional platform-specific telemetry.

Processes can exit between discovery and sampling, especially when unloading a probe model. Missing or zombie processes are excluded from CPU and footprint samples instead of failing the model. Unavailable telemetry for a live process still aborts; CPU errors include the PID and underlying exception to distinguish permission failures from normal process exit.

Metadata HTTP/DNS runs in an owned subprocess with byte limits, a deadline and watchdog checks, so a stalled network request cannot bypass monitoring. The model-store watchdog allows the catalog's staging multiplier; final downloaded model layer sizes must exactly match the verified manifest. Config blobs must match the actual verified config size and SHA-256; a stale descriptor size alone does not invalidate digest-verified config bytes. Frozen tag digest drift produces a skip and requires a catalog review; the runner never relaxes that integrity check automatically.

Local verification supports Ollama's `manifests-v2/ollama.com/` layout, including links to content-addressed manifest blobs, and the older `manifests/registry.ollama.ai/` layout. The v2 entry takes precedence when both exist. Both formats require the full admitted SHA-256 to match; missing files, dangling links, links outside the owned store and actual digest mismatches have distinct errors.


## Related Documentation

- [Model catalog](model-catalog.md)
- [Runner lifecycle](runner-lifecycle.md)
- [Benchmark methodology](benchmarking.md)

## Command Output and Metadata Transport

Ordinary commands retain complete stdout/stderr under a combined 32 MiB cap and abort on overflow so inference timings and metadata are never silently truncated. Serial and paired model pulls instead continuously drain both pipes and retain only the final 8 MiB per stream (16 MiB per download). Progress events are extracted from recent output; total progress volume cannot abort a long download. Existing timeouts, resource watchdogs, exit-code handling and owned-process cleanup still apply. Up to two pulls retain at most 32 MiB of diagnostic output in total.

Metadata workers return base64 to preserve exact HTTP response bytes across the text command interface. The 32 MiB command cap accommodates a full 16 MiB metadata response after base64 expansion. Config responses use that metadata ceiling rather than their descriptor size as a read limit; the digest is mandatory and admission accounts for actual bytes. Neither output limit changes the RAM or disk admission policies.
