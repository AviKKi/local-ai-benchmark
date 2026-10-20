# Benchmark Run

- Run: `2026-10-20T205837.438946Z`
- Device: `mac16-11-64gib`
- Status: interrupted
- Catalog: 2026-10-21
- Ollama: ollama version is 0.40.6

Decoding throughput includes generated thinking tokens where reported by Ollama. Probes and warmups are excluded. Batch requests run sequentially. Output quality is not scored.

| Model | Status | Profile | Decode tok/s | End-to-end tok/s | Reason |
| --- | --- | --- | ---: | ---: | --- |
| gemma3:270m-it-q8_0 | completed | single | 309.24 | 208.74 |  |
| gemma3:270m-it-q8_0 | completed | batch_sequential | 326.86 | 301.02 |  |
| qwen3:0.6b-q4_K_M | completed | single | 256.96 | 251.63 |  |
| qwen3:0.6b-q4_K_M | completed | batch_sequential | 257.57 | 250.21 |  |
| gemma3:1b-it-q4_K_M | completed | single | 175.90 | 172.57 |  |
| gemma3:1b-it-q4_K_M | completed | batch_sequential | 176.93 | 171.73 |  |
| llama3.2:1b-instruct-q4_K_M | completed | single | 234.38 | 229.98 |  |
| llama3.2:1b-instruct-q4_K_M | completed | batch_sequential | 233.74 | 223.62 |  |
| qwen2.5-coder:1.5b-instruct-q4_K_M | completed | single | 169.59 | 166.99 |  |
| qwen2.5-coder:1.5b-instruct-q4_K_M | completed | batch_sequential | 169.29 | 164.08 |  |
| qwen3.5:0.8b-q8_0 | completed | single | 158.25 | 155.96 |  |
| qwen3.5:0.8b-q8_0 | completed | batch_sequential | 159.18 | 155.34 |  |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | completed | single | 169.25 | 166.97 |  |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | completed | batch_sequential | 168.41 | 163.92 |  |
| qwen3:1.7b-q4_K_M | completed | single | 149.74 | 147.72 |  |
| qwen3:1.7b-q4_K_M | completed | batch_sequential | 151.28 | 147.27 |  |
| qwen3.5:2b-q4_K_M | completed | single | 119.51 | 117.93 |  |
| qwen3.5:2b-q4_K_M | completed | batch_sequential | 118.05 | 114.82 |  |
| llama3.2:3b-instruct-q4_K_M | completed | single | 99.75 | 98.61 |  |
| llama3.2:3b-instruct-q4_K_M | completed | batch_sequential | 99.44 | 96.88 |  |
| granite4.2:3b-q4_K_M | completed | single | 88.21 | 87.32 |  |
| granite4.2:3b-q4_K_M | completed | batch_sequential | 88.16 | 85.67 |  |
| phi4-mini:3.8b-q4_K_M | completed | single | 79.71 | 78.94 |  |
| phi4-mini:3.8b-q4_K_M | completed | batch_sequential | 79.50 | 77.60 |  |
| ministral-3:3b-instruct-2512-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| qwen3.5:4b-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| gemma4:e2b-it-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| qwen2.5-coder:7b-instruct-q4_K_M | skipped | — | — | — | Command exited 1: 10007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l[?2026h[?25l[A[1Gpulling manifest [K pulling 60e05f210007: 100% ▕█████████████████ ▏ 4.7 GB/4.7 GB   12 MB/s      0s[K[?25h[?2026l Error: Head "https://registry.ollama.ai/v2/library/qwen2.5-coder/blobs/sha256:66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e": net/http: TLS handshake timeout |
| lfm2.5:8b-a1b-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| qwen3:8b-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| granite4.2:8b-q4_K_M | completed | single | 42.63 | 42.34 |  |
| granite4.2:8b-q4_K_M | completed | batch_sequential | 42.43 | 41.34 |  |
| ministral-3:8b-instruct-2512-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| gemma4:e4b-it-q4_K_M | completed | single | 84.73 | 82.70 |  |
| gemma4:e4b-it-q4_K_M | completed | batch_sequential | 84.55 | 81.14 |  |
| ornith-1.5:9b | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| qwen3.5:9b-q4_K_M | completed | single | 39.44 | 39.07 |  |
| qwen3.5:9b-q4_K_M | completed | batch_sequential | 39.27 | 38.22 |  |
| gemma4:12b-it-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata fetch failed: The read operation timed out |
| deepseek-r1:14b-qwen-distill-q4_K_M | completed | single | 26.39 | 26.24 |  |
| deepseek-r1:14b-qwen-distill-q4_K_M | completed | batch_sequential | 26.17 | 25.54 |  |
| ministral-3:14b | completed | single | 27.79 | 27.63 |  |
| ministral-3:14b | completed | batch_sequential | 27.57 | 26.92 |  |
| phi4:14b-q4_K_M | interrupted | — | — | — | user_interrupt |

## Run Error

Interrupted; owned processes and artifacts were cleaned up unless a cleanup error is reported

## System Specifications

```json
{
  "os": "Darwin",
  "os_version": "26.5.1",
  "architecture": "arm64",
  "model": "Mac16,11",
  "chip": "Apple M4 Pro",
  "logical_cpu_count": 14,
  "physical_cpu_count": 14,
  "memory": {
    "physical": 68719476736,
    "available": 61136650240,
    "pressure": "normal",
    "swap_used": 0,
    "metal_recommended": null
  },
  "page_size_bytes": 16384,
  "metal_recommended_working_set_bytes": null,
  "metal_working_set_note": "Not exposed by this telemetry provider; the optional catalog limit is not applied."
}
```

Detailed per-request timings, prompts, resource peaks and missing-metric reasons are in [results.json](results.json). Events and skip reasons are in [events.jsonl](events.jsonl).
