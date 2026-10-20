# Benchmark Run

- Run: `2026-10-20T204744.300191Z`
- Device: `mac16-11-64gib`
- Status: completed
- Catalog: 2026-10-21
- Ollama: ollama version is 0.40.6

Decoding throughput includes generated thinking tokens where reported by Ollama. Probes and warmups are excluded. Batch requests run sequentially. Output quality is not scored.

| Model | Status | Profile | Decode tok/s | End-to-end tok/s | Reason |
| --- | --- | --- | ---: | ---: | --- |
| qwen2.5-coder:1.5b-instruct-q4_K_M | completed | single | 169.32 | 167.08 |  |
| qwen2.5-coder:1.5b-instruct-q4_K_M | completed | batch_sequential | 169.24 | 164.05 |  |

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
    "available": 61105389568,
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
