import json
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

    def test_download_manifest_drift_fails_before_loading(self):
        manifest = Mock(digest="a"*64)
        with self.assertRaisesRegex(BenchmarkError, "manifest digest"):
            self.engine.pull(self.catalog["models"][0], manifest)

    def test_failed_model_cleanup_preserves_neighboring_files(self):
        neighbor = self.workspace / "user-model"
        neighbor.write_text("keep")
        (self.engine.store / "partial").write_text("owned")
        self.engine.stop_server = Mock()
        self.engine.clear_model([], "unused", successful=False)
        self.assertEqual(neighbor.read_text(), "keep")
        self.assertEqual(list(self.engine.store.iterdir()), [])
        self.engine.stop_server.assert_called_once()


if __name__ == "__main__":
    unittest.main()
