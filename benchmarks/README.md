# Benchmark Results

Measured run reports are listed below. Each report records the device, model settings, resource measurements and skipped models.

The first measurements cover a Mac mini with Apple M4 Pro and 64 GiB RAM. Interrupted runs retain their status; only completed model records count as measurements.

## Run Reports

<!-- BENCHMARK-RUNS:START -->
- [2026-10-20T233259.487506Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T233259.487506Z/report.md) · 38 completed model(s); run completed.
- [2026-10-20T205837.438946Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T205837.438946Z/report.md) · 17 completed model(s); run interrupted.
- [2026-10-20T204744.300191Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T204744.300191Z/report.md) · 1 completed model(s); run completed.
- [2026-10-20T203736.771367Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T203736.771367Z/report.md) · 1 completed model(s); run interrupted.
- [2026-10-20T203625.064704Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T203625.064704Z/report.md) · 1 completed model(s); run completed.
- [2026-10-20T202930.982939Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T202930.982939Z/report.md) · 0 completed model(s); run interrupted.
- [2026-10-20T202838.708984Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T202838.708984Z/report.md) · 0 completed model(s); run completed.
- [2026-10-20T202820.088896Z — mac16-11-64gib](runs/mac16-11-64gib/2026-10-20T202820.088896Z/report.md) · 0 completed model(s); run planned.
<!-- BENCHMARK-RUNS:END -->

Reports are grouped by device and run date under [`runs/`](runs/):

```text
runs/<device-id>/<run-id>/
  results.json
  report.md
```

Each report includes hardware and runtime settings, single-request and sequential-batch results, resource measurements, and reasons for skipped or failed models. See the [benchmark methodology](../architecture/benchmarking.md) for the output and publication contract.

[Back to the project](../README.md) · [Roadmap](../architecture/roadmap.md)
