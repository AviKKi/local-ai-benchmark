# Runner Lifecycle

This document describes how a future runner sets up Ollama, processes models and cleans up. The runner is not implemented yet. CLI argument templates, environment variables, timeouts and teardown rules live in [`models.json`](../models.json).

## Execution Order

1. Read and validate the catalog, check the host, and apply [resource admission checks](resource-safety.md) before installing or downloading anything.

2. Take an exclusive run lock and use a fresh, run-owned model store plus an owned `ollama serve` process on the configured loopback port. Refuse an occupied port. Verify the daemon received the configured environment and uses the intended store. Merely setting variables on an `ollama run` client does not configure an already-running server. Check `ollama serve --help` and model/backend support for the installed version; unsupported options or formats must produce a skip.

3. Resolve and verify the manifest, check disk capacity, and install Ollama if needed. Recheck resources after installation and before pulling. Follow [resource safety](resource-safety.md) for the complete rules.

4. Pull one model and verify the local digest against the resolved manifest. Create a run-owned alias from `engine.modelfile_template` so the CLI uses the pinned context, output and prompt-processing limits. Admit its smoke load under the same memory budget. Check actual context and backend with `ollama ps`; skip CPU/mixed offload or mismatched settings. Record actual quantization and reasoning behavior. Recheck resource availability before each request.

5. Run the [benchmark profiles](benchmarking.md), checking resources before every request and running the watchdog throughout setup, download, load and inference. On a timeout or watchdog trigger, stop only the owned server and wait for exit before cleanup or recovery.

6. After each model, unload it, remove the temporary alias and source tag, and verify unload and free space before proceeding. Handle success, failure and interruption. Failed pulls may leave partial blobs: remove them only inside the exclusive run-owned store after stopping its server. Never remove preexisting user models or assume `ollama rm` reclaimed shared blobs. An unload/cleanup failure stops the run. Shut down the owned server during final teardown.

## Ownership and Recovery

Use argument arrays directly instead of shell-interpolated commands. Keep temporary aliases, files, downloads and the daemon associated with one run. Handle interruption with the same cleanup rules as other failures.

Record each model as successful, skipped or failed, with a reason when applicable. Restart the owned server after an abort only when cleanup succeeds and live health checks pass. Stop the entire run on an unload or cleanup failure.


## Related Documentation

- [Resource safety](resource-safety.md)
- [Model catalog](model-catalog.md)
- [Benchmark methodology](benchmarking.md)
