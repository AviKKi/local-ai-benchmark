# Benchmark Run

- Run: `2026-10-20T202838.708984Z`
- Device: `mac16-11-64gib`
- Status: completed
- Catalog: 2026-10-21
- Ollama: not started

Decoding throughput includes generated thinking tokens where reported by Ollama. Probes and warmups are excluded. Batch requests run sequentially. Output quality is not scored.

| Model | Status | Profile | Decode tok/s | End-to-end tok/s | Reason |
| --- | --- | --- | ---: | ---: | --- |
| gemma3:270m-it-q8_0 | skipped | — | — | — | Command exited 1: ments/sideprojects/local-ai-benchmarks/.benchmark-work/run-57inympc/installer-cache Formulae may access personal data in this directory. Warning: The sandbox cannot prevent formulae from reading:   /Users/avikki/Documents because this required path is inside it:   /Users/avikki/Documents/sideprojects/local-ai-benchmarks/.benchmark-work/run-57inympc/installer-cache Formulae may access personal data in this directory. Warning: The sandbox cannot prevent formulae from reading:   /Users/avikki/Documents because this required path is inside it:   /Users/avikki/Documents/sideprojects/local-ai-benchmarks/.benchmark-work/run-57inympc/installer-cache Formulae may access personal data in this directory. Warning: The sandbox cannot prevent formulae from reading:   /Users/avikki/Documents because this required path is inside it:   /Users/avikki/Documents/sideprojects/local-ai-benchmarks/.benchmark-work/run-57inympc/installer-cache Formulae may access personal data in this directory. Warning: The sandbox cannot prevent formulae from reading:   /Users/avikki/Documents because this required path is inside it:   /Users/avikki/Documents/sideprojects/local-ai-benchmarks/.benchmark-work/run-57inympc/installer-cache Formulae may access personal data in this directory. Warning: running over SSH without /dev/console ownership, using user/* instead of gui/* domain! Hide this warning by setting `HOMEBREW_SERVICES_NO_DOMAIN_WARNING=1`. Hide these hints with `HOMEBREW_NO_ENV_HINTS=1` (see `man brew`). |
| qwen3:0.6b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma3:1b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| llama3.2:1b-instruct-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen2.5-coder:1.5b-instruct-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:0.8b-q8_0 | skipped | — | — | — | cli_model_limit_reached |
| deepseek-r1:1.5b-qwen-distill-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3:1.7b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:2b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| llama3.2:3b-instruct-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| granite4.2:3b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| phi4-mini:3.8b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| ministral-3:3b-instruct-2512-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:4b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma4:e2b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen2.5-coder:7b-instruct-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| lfm2.5:8b-a1b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3:8b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| granite4.2:8b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| ministral-3:8b-instruct-2512-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma4:e4b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| ornith-1.5:9b | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:9b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma4:12b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| deepseek-r1:14b-qwen-distill-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| ministral-3:14b | skipped | — | — | — | cli_model_limit_reached |
| phi4:14b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3:14b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gpt-oss:20b | skipped | — | — | — | cli_model_limit_reached |
| devstral-small-2:24b-instruct-2512-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| lfm2.5:24b-a2b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| mistral-small3.2:24b | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:27b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.6:27b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma4:26b-a4b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| granite4.2:30b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| muse-glimmer:30b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.8:27b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| glm-4.7-flash:q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| north-mini-code-1.0:q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| olmo-3.1:32b-instruct-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| olmo-3.1:32b-think-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3-coder:30b-a3b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| deepseek-r1:32b-qwen-distill-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gemma4:31b-it-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3:32b | skipped | — | — | — | cli_model_limit_reached |
| qwen3.5:35b-a3b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| ornith-1.5:35b | skipped | — | — | — | cli_model_limit_reached |
| qwen3.6:35b-a3b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| nemotron-3.5-lightning:30b-a3b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| llama3.3:70b | skipped | — | — | — | cli_model_limit_reached |
| qwen3-coder-next:q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| gpt-oss:120b | skipped | — | — | — | cli_model_limit_reached |
| ornith-1.5:122b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| nemotron-3.5-super:120b-a12b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| laguna-s-2.1:q4_K_M | skipped | — | — | — | cli_model_limit_reached |
| qwen3.8-flash-next:125b-a6b-q4_K_M | skipped | — | — | — | cli_model_limit_reached |
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
    "available": 61425713152,
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
