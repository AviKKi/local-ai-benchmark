import json
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from local_bench.config import BenchmarkError, SafetyError, load_catalog
from local_bench.engine import Ollama
from local_bench.processes import CommandResult, CommandRunner

ROOT = Path(__file__).resolve().parents[1]


class EngineCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)
        self.catalog = load_catalog(ROOT / "models.json")
        commands = CommandRunner(self.catalog["policy"], self.workspace, lambda *args: None)
        self.engine = Ollama(self.catalog, commands, self.workspace, self.workspace)
        self.engine.cli = Mock()

    def listing(self, *rows):
        self.engine.cli.return_value = CommandResult("NAME ID SIZE PROCESSOR CONTEXT UNTIL\n" + "\n".join(rows) + "\n", "", 0.1)

    def test_requires_full_gpu_and_exact_context(self):
        self.listing("alias:latest abcd 1 GB 100% GPU 2048 2 minutes")
        self.engine.verify_loaded("alias")

    def test_rejects_cpu_offload(self):
        self.listing("alias:latest abcd 1 GB 50%/50% CPU/GPU 2048 2 minutes")
        with self.assertRaisesRegex(SafetyError, "backend/context"):
            self.engine.verify_loaded("alias")

    def test_rejects_larger_context(self):
        self.listing("alias:latest abcd 1 GB 100% GPU 131072 2 minutes")
        with self.assertRaisesRegex(SafetyError, "backend/context"):
            self.engine.verify_loaded("alias")

    def test_rejects_second_loaded_model(self):
        self.listing("alias:latest abcd 1 GB 100% GPU 2048 2 minutes", "other:latest efgh 1 GB 100% GPU 2048 2 minutes")
        with self.assertRaisesRegex(SafetyError, "exactly one"):
            self.engine.verify_loaded("alias")

    def test_quantization_mismatch(self):
        self.engine.cli.return_value = CommandResult("Model\n  quantization Q8_0\n", "", 0.1)
        with self.assertRaisesRegex(BenchmarkError, "Quantization mismatch"):
            self.engine.inspect("alias", "Q4_K_M")
        self.assertEqual(self.engine.inspect("alias", None), "Q8_0")

    def test_unsupported_parameters_fail_closed(self):
        self.engine.cli.return_value = CommandResult("num_ctx 2048\nnum_predict 256\n", "", 0.1)
        with self.assertRaisesRegex(BenchmarkError, "num_batch"):
            self.engine.create_alias(self.catalog["models"][0])

    def test_missing_download_manifest_has_distinct_error(self):
        manifest = Mock(digest="a"*64)
        with self.assertRaisesRegex(BenchmarkError, "manifest not found"):
            self.engine.pull(self.catalog["models"][0], manifest)

    def manifest_fixture(self, directory="manifests-v2", host="ollama.com", linked=False):
        model = self.catalog["models"][0]
        family, revision = model["ollama_tag"].split(":")
        raw = json.dumps({"schemaVersion": 2, "layers": []}).encode()
        manifest = Mock(digest=hashlib.sha256(raw).hexdigest())
        local = self.engine.store / directory / host / "library" / family / revision
        local.parent.mkdir(parents=True, exist_ok=True)
        if linked:
            blob = self.engine.store / "blobs" / f"sha256-{manifest.digest}"
            blob.parent.mkdir(parents=True, exist_ok=True)
            blob.write_bytes(raw)
            local.symlink_to(os.path.relpath(blob, local.parent))
        else:
            local.write_bytes(raw)
        return model, manifest, local

    def test_legacy_manifest_verified(self):
        model, manifest, _ = self.manifest_fixture("manifests", "registry.ollama.ai")
        self.engine.verify_downloaded_manifest(model, manifest)

    def test_legacy_public_host_alias_verified(self):
        model, manifest, _ = self.manifest_fixture("manifests", "ollama.com")
        self.engine.verify_downloaded_manifest(model, manifest)

    def test_v2_copied_manifest_verified(self):
        model, manifest, _ = self.manifest_fixture()
        self.engine.verify_downloaded_manifest(model, manifest)

    def test_v2_content_addressed_symlink_verified(self):
        model, manifest, _ = self.manifest_fixture(linked=True)
        self.engine.verify_downloaded_manifest(model, manifest)

    def test_v2_takes_precedence_over_legacy_manifest(self):
        model, manifest, local = self.manifest_fixture()
        self.manifest_fixture("manifests", "registry.ollama.ai")
        local.write_bytes(b"changed manifest")
        with self.assertRaisesRegex(BenchmarkError, "manifest digest differs"):
            self.engine.verify_downloaded_manifest(model, manifest)

    def test_content_addressed_manifest_still_requires_hash_match(self):
        model, manifest, local = self.manifest_fixture(linked=True)
        local.write_bytes(b"corrupted blob")
        with self.assertRaisesRegex(BenchmarkError, "manifest digest differs"):
            self.engine.verify_downloaded_manifest(model, manifest)

    def test_manifest_symlink_cannot_leave_owned_store(self):
        model, manifest, local = self.manifest_fixture()
        outside = self.workspace / "outside-manifest"
        outside.write_bytes(local.read_bytes())
        local.unlink()
        local.symlink_to(outside)
        with self.assertRaisesRegex(BenchmarkError, "outside the owned"):
            self.engine.verify_downloaded_manifest(model, manifest)

    def test_dangling_manifest_link_fails_closed(self):
        model, manifest, local = self.manifest_fixture(linked=True)
        local.resolve().unlink()
        with self.assertRaisesRegex(BenchmarkError, "Cannot read downloaded manifest"):
            self.engine.verify_downloaded_manifest(model, manifest)

    def test_manifest_size_is_bounded(self):
        model, manifest, local = self.manifest_fixture()
        self.engine.policy["disk"]["maximum_manifest_bytes"] = 4
        with self.assertRaisesRegex(BenchmarkError, "metadata byte limit"):
            self.engine.verify_downloaded_manifest(model, manifest)

    def test_failed_model_cleanup_preserves_neighboring_files(self):
        neighbor = self.workspace / "user-model"
        neighbor.write_text("keep")
        (self.engine.store / "partial").write_text("owned")
        self.engine.stop_server = Mock()
        self.engine.clear_model([], "unused", successful=False)
        self.assertEqual(neighbor.read_text(), "keep")
        self.assertEqual(list(self.engine.store.iterdir()), [])
        self.engine.stop_server.assert_called_once()

    def test_successful_cleanup_can_preserve_queued_model_store(self):
        queued = self.engine.store / "queued-weights"
        queued.write_bytes(b"owned")
        self.engine.commands.server = Mock()
        self.engine.cli.return_value = CommandResult("NAME ID SIZE PROCESSOR CONTEXT UNTIL\n", "", 0.1)
        self.engine.stop_server = Mock()
        self.engine.clear_model(["alias"], "source", True, preserve_store=True)
        self.assertEqual(queued.read_bytes(), b"owned")
        self.engine.cli.assert_any_call("rm", "source")
        self.engine.stop_server.assert_called_once()

    def test_restart_accepts_only_expected_queued_model_names(self):
        self.engine.cli.return_value = CommandResult("NAME ID SIZE\nqwen3:8b-q4_K_M abc 5GB\n", "", 0.1)
        self.engine.verify_store(["qwen3:8b-q4_K_M"])
        with self.assertRaisesRegex(SafetyError, "unexpected models"):
            self.engine.verify_store()

    def test_paired_pull_verifies_success_even_when_other_pull_fails(self):
        self.engine.commands.pull_many = Mock(return_value=[CommandResult("", "", 1, 0), CommandResult("", "network timeout", 1, 1)])
        self.engine.verify_download = Mock()
        models = self.catalog["models"][:2]
        manifest = Mock()
        errors = self.engine.pull_many([(model, manifest) for model in models])
        self.assertIsNone(errors[0])
        self.assertIn("network timeout", errors[1])
        self.engine.verify_download.assert_called_once_with(models[0], manifest)


if __name__ == "__main__":
    unittest.main()
