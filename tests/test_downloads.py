import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_runner

from local_bench.cli import main
from local_bench.config import BenchmarkError, SafetyError, load_catalog, validate_catalog
from local_bench.downloads import storage_model
from local_bench.processes import CommandRunner, OwnedProcess
from local_bench.registry import Manifest
from local_bench.safety import Guard


ROOT = Path(__file__).resolve().parents[1]


class BatchEngine(test_runner.FakeEngine):
    instance = None
    failed_pull = None
    failed_inference = None
    interrupt_pull = False

    def __init__(self, catalog, commands, workspace, result_dir):
        super().__init__(catalog, commands, workspace, result_dir)
        type(self).instance = self
        self.cached = set()
        self.trace = []
        self.live = False

    def start(self, expected_models=()):
        if not self.live:
            if not self.cached.issubset(set(expected_models)):
                raise AssertionError("Unexpected cached models")
            self.trace.append(("start", tuple(expected_models)))
            self.live = True

    def pull(self, model, manifest):
        self.trace.append(("pull", model["ollama_tag"]))
        self.cached.add(model["ollama_tag"])

    def pull_many(self, items):
        self.trace.append(("pair", tuple(model["ollama_tag"] for model, _ in items)))
        if self.interrupt_pull:
            raise KeyboardInterrupt
        errors = []
        for model, _ in items:
            tag = model["ollama_tag"]
            errors.append("simulated network timeout" if tag == self.failed_pull else None)
            if tag != self.failed_pull:
                self.cached.add(tag)
        return errors

    def verify_download(self, model, manifest):
        if model["ollama_tag"] not in self.cached:
            raise AssertionError("Queued model was not retained")

    def create_alias(self, model, probe=False):
        self.current = model["ollama_tag"]
        self.trace.append(("infer", self.current))
        if self.current not in self.cached:
            raise AssertionError("Inference attempted before download")
        if self.current == self.failed_inference:
            raise SafetyError("simulated inference failure")
        return super().create_alias(model, probe)

    def clear_model(self, aliases, source, successful, preserve_store=False):
        self.trace.append(("clear", source, preserve_store))
        self.live = False
        if preserve_store:
            self.cached.discard(source)
        else:
            self.cached.clear()


class PairPipelineCase(unittest.TestCase):
    def setUp(self):
        BatchEngine.failed_pull = BatchEngine.failed_inference = None
        BatchEngine.interrupt_pull = False
        BatchEngine.fail_request = False
        BatchEngine.request_count = 0
        self.catalog = load_catalog(ROOT / "models.json")
        self.catalog["models"] = self.catalog["models"][:3]

    def run_fake(self, root, extra=(), disk=None):
        catalog_path = root / "models.json"
        catalog_path.write_text(json.dumps(self.catalog))

        def resolve(model, guard):
            return Manifest(model["provenance"]["observed_manifest_sha256_prefix"].ljust(64, "a"), {}, 300, model["quantization"])

        with patch("local_bench.cli.MacTelemetry", test_runner.FakeTelemetry), patch("local_bench.cli.Ollama", BatchEngine), patch("local_bench.cli.Registry.resolve", side_effect=resolve), patch("local_bench.downloads.disk_reason", side_effect=disk or (lambda *args, **kwargs: None)), patch("local_bench.safety.disk_reason", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            code = main(["--models-file", str(catalog_path), "--output-dir", str(root / "results"),
                         "--work-dir", str(root / "work"), "--no-ui", *extra])
        path = max((root / "results").rglob("results.json"), key=lambda item: item.parent.name)
        self.assertFalse(list((root / "work").glob("run-*")))
        self.assertFalse(BatchEngine.instance.cached)
        return code, json.loads(path.read_text()), BatchEngine.instance.trace

    def test_download_pair_then_serial_inference_with_odd_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, report, trace = self.run_fake(Path(temporary))
        self.assertEqual(code, 0)
        self.assertEqual([record["status"] for record in report["models"]], ["completed"] * 3)
        self.assertEqual([item[0] for item in trace].count("pair"), 1)
        self.assertEqual([item[0] for item in trace].count("pull"), 1)
        self.assertLess(next(index for index, item in enumerate(trace) if item[0] == "pair"), next(index for index, item in enumerate(trace) if item[0] == "infer"))
        self.assertTrue(any(item[0] == "clear" and item[2] for item in trace))
        self.assertTrue(all(not record["downloads_during_inference"] for record in report["models"]))
        self.assertEqual([record["download_concurrency"] for record in report["models"]], [2, 2, 1])

    def test_serial_override_retains_old_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, report, trace = self.run_fake(Path(temporary), ("--download-workers", "1"))
        self.assertEqual(code, 0)
        self.assertNotIn("pair", [item[0] for item in trace])
        self.assertEqual([record["status"] for record in report["models"]], ["completed"] * 3)

    def test_pair_disk_budget_failure_falls_back_to_serial(self):
        maximum = max(model["resources"]["download_bytes_upper_bound"] for model in self.catalog["models"])
        def disk(model, *args, **kwargs):
            return "insufficient_disk_space:pair" if kwargs.get("admission", True) and model["resources"]["download_bytes_upper_bound"] > maximum else None
        with tempfile.TemporaryDirectory() as temporary:
            code, report, trace = self.run_fake(Path(temporary), disk=disk)
        self.assertEqual(code, 0)
        self.assertNotIn("pair", [item[0] for item in trace])
        self.assertEqual([record["status"] for record in report["models"]], ["completed"] * 3)

    def test_one_failed_pull_does_not_discard_the_other_success(self):
        BatchEngine.failed_pull = self.catalog["models"][0]["ollama_tag"]
        with tempfile.TemporaryDirectory() as temporary:
            code, report, _ = self.run_fake(Path(temporary), ("--limit", "2"))
        self.assertEqual(code, 0)
        self.assertEqual([record["status"] for record in report["models"][:2]], ["skipped", "completed"])
        self.assertEqual(report["models"][1]["download_concurrency"], 2)

    def test_inference_failure_invalidates_cache_and_redownloads_next_safely(self):
        BatchEngine.failed_inference = self.catalog["models"][0]["ollama_tag"]
        with tempfile.TemporaryDirectory() as temporary:
            code, report, trace = self.run_fake(Path(temporary), ("--limit", "2"))
        self.assertEqual(code, 0)
        self.assertEqual(report["models"][1]["status"], "completed")
        self.assertTrue(report["models"][1]["redownload_after_batch_failure"])
        self.assertIn(("pull", self.catalog["models"][1]["ollama_tag"]), trace)

    def test_limit_does_not_prefetch_an_extra_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, report, trace = self.run_fake(Path(temporary), ("--limit", "1"))
        self.assertNotIn("pair", [item[0] for item in trace])
        self.assertEqual([record["status"] for record in report["models"]], ["completed", "skipped", "skipped"])

    def test_resume_does_not_download_already_completed_pairs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.run_fake(root)
            _, report, trace = self.run_fake(root, ("--resume",))
        self.assertFalse(trace)
        self.assertTrue(all(record.get("reused_from") for record in report["models"]))

    def test_interrupt_marks_both_models_and_cleans_workspace(self):
        BatchEngine.interrupt_pull = True
        with tempfile.TemporaryDirectory() as temporary:
            code, report, _ = self.run_fake(Path(temporary))
        self.assertEqual(code, 130)
        self.assertEqual(report["status"], "interrupted")
        self.assertEqual([record["status"] for record in report["models"]], ["interrupted"] * 2)

    def test_storage_guard_uses_combined_disk_but_one_model_memory(self):
        combined = storage_model(self.catalog["models"], self.catalog["policy"])
        self.assertEqual(combined["resources"]["download_bytes_upper_bound"], sum(model["resources"]["download_bytes_upper_bound"] for model in self.catalog["models"]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = self.catalog["models"][0]
            guard = Guard(test_runner.FakeTelemetry(), model, self.catalog["policy"], {}, root, root, lambda: [], storage_model=combined)
            with patch("local_bench.safety.disk_reason", return_value=None) as disk:
                guard.admit()
                self.assertIs(disk.call_args.args[0], combined)
            self.assertIs(guard.model, model)

    def test_higher_download_limits_are_rejected(self):
        for value in (3, 4, 6, True, 2.0):
            self.catalog["policy"]["execution"]["max_concurrent_downloads"] = value
            with self.assertRaises(BenchmarkError):
                validate_catalog(self.catalog)


class ParallelPullCase(unittest.TestCase):
    def setUp(self):
        self.policy = load_catalog(ROOT / "models.json")["policy"]
        self.children = patch("psutil.Process.children", return_value=[])
        self.children.start()
        self.addCleanup(self.children.stop)

    def run_pulls(self, script, timeout=5, guard=None):
        children = []
        def spawn(args, env, cwd):
            owned = OwnedProcess([sys.executable, "-c", script, args[-1]], env, cwd)
            children.append(owned.child)
            return owned
        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            runner.guard = guard
            with patch("local_bench.processes.OwnedProcess", side_effect=spawn):
                try:
                    return runner.pull_many([[sys.executable, "pull", tag] for tag in ("first", "second")], os.environ.copy(), timeout)
                finally:
                    self.assertTrue(all(child.poll() is not None for child in children))
                    self.assertTrue(all(child.stdout.closed and child.stderr.closed for child in children))
                    self.assertEqual(runner.downloads, [])

    def test_both_downloads_complete_and_preserve_return_codes(self):
        results = self.run_pulls("import sys,time; print('100%'); time.sleep(0.05); sys.exit(1 if sys.argv[-1]=='first' else 0)")
        self.assertEqual([result.returncode for result in results], [1, 0])

    def test_timeout_cancels_every_download(self):
        with self.assertRaisesRegex(SafetyError, "parallel_pull"):
            self.run_pulls("import time; time.sleep(30)", timeout=0.05)

    def test_output_limit_cancels_every_download(self):
        self.policy["execution"]["maximum_captured_output_bytes_per_request"] = 100
        with self.assertRaisesRegex(SafetyError, "output_limit"):
            self.run_pulls("print('x'*1000)")

    def test_watchdog_failure_cancels_every_download(self):
        guard = Mock()
        guard.check.side_effect = SafetyError("swap_growth")
        with self.assertRaisesRegex(SafetyError, "swap_growth"):
            self.run_pulls("import time; time.sleep(30)", guard=guard)

    def test_concurrent_inference_is_not_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            with self.assertRaisesRegex(BenchmarkError, "restricted"):
                runner.pull_many([[sys.executable, "run", "model"]], {}, 5)
