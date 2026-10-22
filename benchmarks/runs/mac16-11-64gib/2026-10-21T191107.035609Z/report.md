# Benchmark Run

- Run: `2026-10-21T191107.035609Z`
- Device: `mac16-11-64gib`
- Status: completed
- Catalog: 2026-10-21
- Ollama: ollama version is 0.40.6

Decoding throughput includes generated thinking tokens where reported by Ollama. Probes and warmups are excluded. Batch requests run sequentially. Output quality is not scored.

| Model | Status | Profile | Decode tok/s | End-to-end tok/s | Reason |
| --- | --- | --- | ---: | ---: | --- |
| gemma3:270m-it-q8_0 | reused | single | 309.24 | 208.74 | Measured in 2026-10-20T205837.438946Z |
| gemma3:270m-it-q8_0 | reused | batch_sequential | 326.86 | 301.02 | Measured in 2026-10-20T205837.438946Z |
| qwen3:0.6b-q4_K_M | reused | single | 256.96 | 251.63 | Measured in 2026-10-20T205837.438946Z |
| qwen3:0.6b-q4_K_M | reused | batch_sequential | 257.57 | 250.21 | Measured in 2026-10-20T205837.438946Z |
| llama3.2:1b-instruct-q4_K_M | reused | single | 234.38 | 229.98 | Measured in 2026-10-20T205837.438946Z |
| llama3.2:1b-instruct-q4_K_M | reused | batch_sequential | 233.74 | 223.62 | Measured in 2026-10-20T205837.438946Z |
| gemma3:1b-it-q4_K_M | reused | single | 175.90 | 172.57 | Measured in 2026-10-20T205837.438946Z |
| gemma3:1b-it-q4_K_M | reused | batch_sequential | 176.93 | 171.73 | Measured in 2026-10-20T205837.438946Z |
| qwen2.5-coder:1.5b-instruct-q4_K_M | reused | single | 169.59 | 166.99 | Measured in 2026-10-20T205837.438946Z |
| qwen2.5-coder:1.5b-instruct-q4_K_M | reused | batch_sequential | 169.29 | 164.08 | Measured in 2026-10-20T205837.438946Z |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | reused | single | 169.25 | 166.97 | Measured in 2026-10-20T205837.438946Z |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | reused | batch_sequential | 168.41 | 163.92 | Measured in 2026-10-20T205837.438946Z |
| qwen3.5:0.8b-q8_0 | reused | single | 158.25 | 155.96 | Measured in 2026-10-20T205837.438946Z |
| qwen3.5:0.8b-q8_0 | reused | batch_sequential | 159.18 | 155.34 | Measured in 2026-10-20T205837.438946Z |
| lfm2.5:8b-a1b-q4_K_M | reused | single | 151.85 | 149.24 | Measured in 2026-10-20T233259.487506Z |
| lfm2.5:8b-a1b-q4_K_M | reused | batch_sequential | 151.88 | 145.43 | Measured in 2026-10-20T233259.487506Z |
| qwen3:1.7b-q4_K_M | reused | single | 149.74 | 147.72 | Measured in 2026-10-20T205837.438946Z |
| qwen3:1.7b-q4_K_M | reused | batch_sequential | 151.28 | 147.27 | Measured in 2026-10-20T205837.438946Z |
| gemma4:e2b-it-q4_K_M | reused | single | 123.37 | 120.94 | Measured in 2026-10-20T233259.487506Z |
| gemma4:e2b-it-q4_K_M | reused | batch_sequential | 135.62 | 130.18 | Measured in 2026-10-20T233259.487506Z |
| qwen3.5:2b-q4_K_M | reused | single | 119.51 | 117.93 | Measured in 2026-10-20T205837.438946Z |
| qwen3.5:2b-q4_K_M | reused | batch_sequential | 118.05 | 114.82 | Measured in 2026-10-20T205837.438946Z |
| lfm2.5:24b-a2b-q4_K_M | reused | single | 101.09 | 99.52 | Measured in 2026-10-20T233259.487506Z |
| lfm2.5:24b-a2b-q4_K_M | reused | batch_sequential | 101.32 | 96.11 | Measured in 2026-10-20T233259.487506Z |
| llama3.2:3b-instruct-q4_K_M | reused | single | 99.75 | 98.61 | Measured in 2026-10-20T205837.438946Z |
| llama3.2:3b-instruct-q4_K_M | reused | batch_sequential | 99.44 | 96.88 | Measured in 2026-10-20T205837.438946Z |
| granite4.2:3b-q4_K_M | reused | single | 88.21 | 87.32 | Measured in 2026-10-20T205837.438946Z |
| granite4.2:3b-q4_K_M | reused | batch_sequential | 88.16 | 85.67 | Measured in 2026-10-20T205837.438946Z |
| ministral-3:3b-instruct-2512-q4_K_M | reused | single | 84.80 | 83.90 | Measured in 2026-10-20T233259.487506Z |
| ministral-3:3b-instruct-2512-q4_K_M | reused | batch_sequential | 84.57 | 82.48 | Measured in 2026-10-20T233259.487506Z |
| gemma4:e4b-it-q4_K_M | reused | single | 84.73 | 82.70 | Measured in 2026-10-20T205837.438946Z |
| gemma4:e4b-it-q4_K_M | reused | batch_sequential | 84.55 | 81.14 | Measured in 2026-10-20T205837.438946Z |
| phi4-mini:3.8b-q4_K_M | reused | single | 79.71 | 78.94 | Measured in 2026-10-20T205837.438946Z |
| phi4-mini:3.8b-q4_K_M | reused | batch_sequential | 79.50 | 77.60 | Measured in 2026-10-20T205837.438946Z |
| north-mini-code-1.0:q4_K_M | reused | single | 76.64 | 75.24 | Measured in 2026-10-20T233259.487506Z |
| north-mini-code-1.0:q4_K_M | reused | batch_sequential | 76.59 | 72.68 | Measured in 2026-10-20T233259.487506Z |
| gemma4:26b-a4b-it-q4_K_M | reused | single | 63.20 | 62.15 | Measured in 2026-10-20T233259.487506Z |
| gemma4:26b-a4b-it-q4_K_M | reused | batch_sequential | 63.30 | 60.70 | Measured in 2026-10-20T233259.487506Z |
| qwen3.5:4b-q4_K_M | reused | single | 59.73 | 59.07 | Measured in 2026-10-20T233259.487506Z |
| qwen3.5:4b-q4_K_M | reused | batch_sequential | 60.51 | 58.90 | Measured in 2026-10-20T233259.487506Z |
| gpt-oss:20b | reused | single | 55.24 | 54.39 | Measured in 2026-10-20T233259.487506Z |
| gpt-oss:20b | reused | batch_sequential | 55.23 | 53.57 | Measured in 2026-10-20T233259.487506Z |
| glm-4.7-flash:q4_K_M | reused | single | 55.21 | 54.76 | Measured in 2026-10-20T233259.487506Z |
| glm-4.7-flash:q4_K_M | reused | batch_sequential | 54.43 | 52.81 | Measured in 2026-10-20T233259.487506Z |
| qwen2.5-coder:7b-instruct-q4_K_M | reused | single | 50.80 | 50.43 | Measured in 2026-10-20T233259.487506Z |
| qwen2.5-coder:7b-instruct-q4_K_M | reused | batch_sequential | 50.77 | 49.54 | Measured in 2026-10-20T233259.487506Z |
| gemma4:12b-it-q4_K_M | reused | single | 49.41 | 48.39 | Measured in 2026-10-20T233259.487506Z |
| gemma4:12b-it-q4_K_M | reused | batch_sequential | 49.26 | 46.77 | Measured in 2026-10-20T233259.487506Z |
| qwen3:8b-q4_K_M | reused | single | 45.19 | 44.86 | Measured in 2026-10-20T233259.487506Z |
| qwen3:8b-q4_K_M | reused | batch_sequential | 44.85 | 43.74 | Measured in 2026-10-20T233259.487506Z |
| ministral-3:8b-instruct-2512-q4_K_M | reused | single | 42.83 | 42.53 | Measured in 2026-10-20T233259.487506Z |
| ministral-3:8b-instruct-2512-q4_K_M | reused | batch_sequential | 42.62 | 41.64 | Measured in 2026-10-20T233259.487506Z |
| granite4.2:8b-q4_K_M | reused | single | 42.63 | 42.34 | Measured in 2026-10-20T205837.438946Z |
| granite4.2:8b-q4_K_M | reused | batch_sequential | 42.43 | 41.34 | Measured in 2026-10-20T205837.438946Z |
| ornith-1.5:9b | reused | single | 39.89 | 39.51 | Measured in 2026-10-20T233259.487506Z |
| ornith-1.5:9b | reused | batch_sequential | 39.73 | 38.59 | Measured in 2026-10-20T233259.487506Z |
| qwen3.5:9b-q4_K_M | reused | single | 39.44 | 39.07 | Measured in 2026-10-20T205837.438946Z |
| qwen3.5:9b-q4_K_M | reused | batch_sequential | 39.27 | 38.22 | Measured in 2026-10-20T205837.438946Z |
| ministral-3:14b | reused | single | 27.79 | 27.63 | Measured in 2026-10-20T205837.438946Z |
| ministral-3:14b | reused | batch_sequential | 27.57 | 26.92 | Measured in 2026-10-20T205837.438946Z |
| deepseek-r1:14b-qwen-distill-q4_K_M | reused | single | 26.39 | 26.24 | Measured in 2026-10-20T205837.438946Z |
| deepseek-r1:14b-qwen-distill-q4_K_M | reused | batch_sequential | 26.17 | 25.54 | Measured in 2026-10-20T205837.438946Z |
| qwen3:14b-q4_K_M | reused | single | 26.16 | 26.01 | Measured in 2026-10-20T233259.487506Z |
| qwen3:14b-q4_K_M | reused | batch_sequential | 25.98 | 25.33 | Measured in 2026-10-20T233259.487506Z |
| phi4:14b-q4_K_M | reused | single | 25.41 | 25.27 | Measured in 2026-10-20T233259.487506Z |
| phi4:14b-q4_K_M | reused | batch_sequential | 25.10 | 24.46 | Measured in 2026-10-20T233259.487506Z |
| mistral-small3.2:24b | completed | single | 17.01 | 16.92 |  |
| mistral-small3.2:24b | completed | batch_sequential | 16.83 | 16.40 |  |
| devstral-small-2:24b-instruct-2512-q4_K_M | reused | single | 16.62 | 16.54 | Measured in 2026-10-20T233259.487506Z |
| devstral-small-2:24b-instruct-2512-q4_K_M | reused | batch_sequential | 16.47 | 16.07 | Measured in 2026-10-20T233259.487506Z |
| qwen3.6:27b-q4_K_M | reused | single | 13.89 | 13.78 | Measured in 2026-10-20T233259.487506Z |
| qwen3.6:27b-q4_K_M | reused | batch_sequential | 13.78 | 13.36 | Measured in 2026-10-20T233259.487506Z |
| granite4.2:30b-q4_K_M | reused | single | 13.43 | 13.37 | Measured in 2026-10-20T233259.487506Z |
| granite4.2:30b-q4_K_M | reused | batch_sequential | 13.26 | 12.89 | Measured in 2026-10-20T233259.487506Z |
| olmo-3.1:32b-instruct-q4_K_M | reused | single | 12.39 | 12.25 | Measured in 2026-10-20T233259.487506Z |
| olmo-3.1:32b-instruct-q4_K_M | reused | batch_sequential | 12.26 | 11.84 | Measured in 2026-10-20T233259.487506Z |
| olmo-3.1:32b-think-q4_K_M | completed | single | 12.37 | 12.23 |  |
| olmo-3.1:32b-think-q4_K_M | completed | batch_sequential | 12.24 | 11.86 |  |
| deepseek-r1:32b-qwen-distill-q4_K_M | completed | single | 12.18 | 12.12 |  |
| deepseek-r1:32b-qwen-distill-q4_K_M | completed | batch_sequential | 12.05 | 11.75 |  |
| qwen3:32b | reused | single | 11.93 | 11.87 | Measured in 2026-10-20T233259.487506Z |
| qwen3:32b | reused | batch_sequential | 11.79 | 11.48 | Measured in 2026-10-20T233259.487506Z |
| qwen3.5:27b-q4_K_M | skipped | — | — | — | command_output_limit_exceeded |
| muse-glimmer:30b-q4_K_M | skipped | — | — | — | command_output_limit_exceeded |
| qwen3.8:27b-q4_K_M | skipped | — | — | — | command_output_limit_exceeded |
| qwen3-coder:30b-a3b-q4_K_M | skipped | — | — | — | Command exited 1: Registry metadata exceeded its byte limit |
| gemma4:31b-it-q4_K_M | skipped | — | — | — | insufficient_available_memory |
| qwen3.5:35b-a3b-q4_K_M | skipped | — | — | — | insufficient_available_memory |
| ornith-1.5:35b | skipped | — | — | — | insufficient_available_memory |
| qwen3.6:35b-a3b-q4_K_M | skipped | — | — | — | insufficient_available_memory |
| nemotron-3.5-lightning:30b-a3b-q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| llama3.3:70b | skipped | — | — | — | physical_memory_below_model_minimum |
| qwen3-coder-next:q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| gpt-oss:120b | skipped | — | — | — | physical_memory_below_model_minimum |
| ornith-1.5:122b-q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| nemotron-3.5-super:120b-a12b-q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| laguna-s-2.1:q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| qwen3.8-flash-next:125b-a6b-q4_K_M | skipped | — | — | — | physical_memory_below_model_minimum |
| bonsai-2:2b | skipped | — | — | — | disabled:New ternary GGUF file type 41 is not identified by the registry UI; confirm installed Ollama/Metal support before enabling. |
| bonsai-2:4b | skipped | — | — | — | disabled:New ternary GGUF file type 41 is not identified by the registry UI; confirm installed Ollama/Metal support before enabling. |
| bonsai-2:9b | skipped | — | — | — | disabled:New ternary GGUF file type 41 is not identified by the registry UI; confirm installed Ollama/Metal support before enabling. |
| bonsai-2:27b | skipped | — | — | — | disabled:New ternary GGUF file type 41 is not identified by the registry UI; confirm installed Ollama/Metal support before enabling. |
| laguna-xs-2.1:q4_K_M | skipped | — | — | — | disabled:Upstream reports an unresolved macOS issue; recheck the model page before enabling. |
| nemotron-3.5-bolt:74b-a9b-iq2 | skipped | — | — | — | disabled:Published mixed IQ2_XXS/NVFP4 artifact does not support Apple Silicon / Metal. |

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
    "available": 58424295424,
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
