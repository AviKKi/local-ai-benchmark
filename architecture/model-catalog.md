# Model Catalog

[`models.json`](../models.json) is the Phase 1 input catalog, researched through **21 October 2026** using the [official Ollama library](https://ollama.com/library?sort=newest). It contains 64 local model variants across 32 families, covering general chat, coding and reasoning, from sub-billion-parameter baselines to models for larger hosts. It is a broad selection, not a claim that every community model has been evaluated for quality.

Current families include Qwen 3.5/3.6/3.8, Gemma 4, Bonsai 2, Granite 4.2, Ministral 3, LFM 2.5, gpt-oss, Qwen3-Coder/Next, GLM-4.7-Flash, Devstral Small 2, Olmo 3.1, North Mini Code, Muse Glimmer, Laguna 2.1, Nemotron 3.5 and Ornith 1.5. Older Qwen, Llama, Gemma, DeepSeek-R1 and Phi variants provide useful small-model and historical comparisons.

Multimodal LLMs are included for **text-only** testing. Embeddings, speech, image generation and decision-only models remain outside Phase 1. The latest DeepSeek-V4.1-Flash, GLM-5.3/Flash, Kimi K3, MiniMax M3.1 Flash and Mistral Large 4 have only cloud tags in the checked official Ollama listings; they are documented under `excluded_families` and must never be substituted for local inference.

The catalog is configuration, **not an implemented benchmark runner**. Its RAM budgets are unmeasured planning estimates. Resource checks and monitoring reduce risk but cannot guarantee that an allocation spike or another application will never cause OOM. A consumer must enforce the [resource safety](resource-safety.md) and [runner lifecycle](runner-lifecycle.md) contracts before downloading or loading anything.

Qwen3-Coder-Next 80B Q3_K_M was added on 22 October 2026 from [Unsloth's GGUF artifact](https://huggingface.co/unsloth/Qwen3-Coder-Next-GGUF/blob/main/Qwen3-Coder-Next-Q3_K_M.gguf), approximately 38.3 GB. This experimental entry remains disabled because the runner only verifies official Ollama library manifests. Its provenance records the GGUF SHA-256 separately with null manifest fields; validation prevents enabling it until import support exists. Its unmeasured 44 GiB peak estimate becomes a 55 GiB budget, requiring at least 57 GiB available RAM at startup and live admission under the new 2 GiB buffer policy. Import support and disk admission remain separate requirements.

## Fields and Units

All capacity fields are integer **bytes**. Registry sizes use decimal GB; policy reserves use binary GiB. `units` gives both conversions.

| Field | Consumer meaning |
| --- | --- |
| `schema_version` | Reject unsupported versions instead of guessing field semantics. |
| `as_of`, `provenance.verified_on` | Research snapshot dates, not model release dates. |
| `ollama_tag` | Download this exact tag, not the family default or `latest`. Tags can still change. |
| `enabled`, `disabled_reason` | Skip disabled entries before any download. |
| `selection_group` | `current`, `baseline`, `experimental` or `large_host`; descriptive, never an admission decision. |
| `compatibility` | Phase 1 host/backend requirements; enabled models still require runtime verification. A null minimum version means unknown, not universally supported. |
| `parameters_billion`, `active_parameters_billion` | Approximate size labels; null means unspecified. MoE memory depends on all weights, not just active experts. |
| `quantization` | Expected quantization when verified; inspect and record the actual artifact when null. |
| `provenance` | Primary source links, registry manifest URL and observed SHA-256 prefix. Resolve and record the full digest at runtime. |
| `resources.published_download_bytes_approx` | Rounded registry size; never use alone for disk admission. Includes the published artifact rather than an FP16 parameter-count calculation. |
| `resources.download_bytes_upper_bound` | Planning cap with rounding margin; the live manifest must fit within it. |
| `resources.estimated_peak_unified_memory_bytes` | Estimated model/runtime memory at the fixed benchmark settings; apply the additional policy multiplier. |
| `resources.minimum_physical_memory_bytes` | Advisory host tier; admission uses the frozen startup available-RAM cap and live RAM checks instead. |
| `policy`, `engine`, `benchmark` | Mandatory admission rules, CLI setup/cleanup, fixed workload and result requirements. |

The four Bonsai 2 variants are disabled pending verification of the new ternary GGUF type on the installed Ollama/Metal backend. [Nemotron 3.5 Bolt explicitly lacks Apple Silicon/Metal support](https://ollama.com/library/nemotron-3.5-bolt:74b-a9b-iq2), and [Laguna XS 2.1 reports an unresolved macOS issue](https://ollama.com/library/laguna-xs-2.1); both are also disabled. Keep their source evidence visible and recheck it before enabling them. Larger entries remain catalogued so a runner can report an informative memory skip on the 16 GB/64 GB Macs and select them on a future larger Mac.

## Related Documentation

- [Resource safety](resource-safety.md)
- [Runner lifecycle](runner-lifecycle.md)
- [Roadmap and scope](roadmap.md)
