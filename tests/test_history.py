import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import test_runner

from local_bench.cli import main
from local_bench.config import BenchmarkError, load_catalog
from local_bench.history import choose_resume, compatible_history, measurement_signature, read_history, reusable_measurements
from local_bench.prompts import PROMPTS


ROOT = Path(__file__).resolve().parents[1]


class HistoryCase(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(ROOT / "models.json")
        self.model = self.catalog["models"][0]
        self.specs = {"os": "Darwin", "os_version": "26.5", "architecture": "arm64", "model": "Mac16,11",
                      "chip": "Apple M4 Pro", "memory": {"physical": 64 * 1024 ** 3, "available": 1}}
        self.record = {"ollama_tag": self.model["ollama_tag"], "model_id": self.model["id"], "status": "completed",
                       "resolved_manifest_sha256": self.model["provenance"]["observed_manifest_sha256_prefix"] + "a" * 52,
                       "actual_quantization": self.model["quantization"], "actual_context_length": 2048,
                       "profiles": [{"id": profile["id"], "concurrency": 1, "requests": [{}] * profile["measured_requests"],
                                     "metrics": {"valid_generation_measurements": profile["measured_requests"], "generation_tokens_per_second": 10}}
                                    for profile in self.catalog["benchmark"]["profiles"]]}
        self.report = {"run_id": "old", "started_at": "2026-10-21", "plan_only": False,
                       "system_specs": self.specs, "catalog_schema_version": self.catalog["schema_version"],
                       "benchmark_options": self.catalog["benchmark"]["options"], "models": [self.record],
                       "prompts": [vars(prompt) for prompt in PROMPTS]}
        self.warning = Mock()

    def reuse(self):
        return reusable_measurements([(Path("results.json"), self.report)], [self.model], self.catalog, self.warning)

    def test_completed_legacy_measurement_is_reused_with_provenance(self):
        reused = self.reuse()[self.model["ollama_tag"]]
        self.assertEqual(reused["reused_from"]["run_id"], "old")
        self.assertNotIn("reused_from", self.record)

    def test_failed_skipped_running_and_partial_measurements_are_not_reused(self):
        for status in ("failed", "skipped", "running", "interrupted", "planned"):
            with self.subTest(status=status):
                self.record["status"] = status
                self.assertFalse(self.reuse())
        self.record["status"] = "completed"
        self.record["profiles"][1]["requests"] = []
        self.assertFalse(self.reuse())

    def test_catalog_digest_drift_requires_retry(self):
        self.record["resolved_manifest_sha256"] = "f" * 64
        self.assertFalse(self.reuse())

    def test_nonfinite_or_missing_timings_require_retry(self):
        for rate in (float("nan"), float("inf"), None, 0):
            self.record["profiles"][0]["metrics"]["generation_tokens_per_second"] = rate
            self.assertFalse(self.reuse())

    def test_host_identity_ignores_available_memory_but_not_chip(self):
        specs = copy.deepcopy(self.specs)
        specs["memory"]["available"] = 100
        self.assertTrue(compatible_history(self.report, specs, self.catalog))
        specs["chip"] = "different chip"
        self.assertFalse(compatible_history(self.report, specs, self.catalog))

    def test_settings_and_signature_mismatch_are_rejected(self):
        report = copy.deepcopy(self.report)
        report["benchmark_options"]["num_ctx"] = 4096
        self.assertFalse(compatible_history(report, self.specs, self.catalog))
        self.report["measurement_signature"] = "different"
        self.assertFalse(compatible_history(self.report, self.specs, self.catalog))
        self.report["measurement_signature"] = measurement_signature(self.catalog)
        self.assertTrue(compatible_history(self.report, self.specs, self.catalog))

    def test_newer_failed_run_does_not_hide_older_success(self):
        failed = copy.deepcopy(self.report)
        failed["models"][0]["status"] = "failed"
        history = [(Path("new.json"), failed), (Path("old.json"), self.report)]
        reused = reusable_measurements(history, [self.model], self.catalog, self.warning)
        self.assertTrue(reused)

    def test_corrupt_history_is_ignored_without_hiding_valid_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, text in (("old", json.dumps(self.report)), ("bad", "{"), ("bad-models", '{"models":null}')):
                directory = root / "device" / name
                directory.mkdir(parents=True)
                (directory / "results.json").write_text(text)
            history = read_history(root, self.specs, self.catalog, self.warning)
        self.assertEqual(len(history), 1)
        self.assertEqual(self.warning.call_count, 2)

    def test_interactive_resume_and_fresh_choices(self):
        for answer, expected in (("r\n", True), ("\n", True), ("f\n", False)):
            stream = Mock()
            stream.isatty.return_value = True
            stream.readline.return_value = answer
            self.assertEqual(choose_resume([(None, self.report)], True, stream, self.warning), expected)

    def test_noninteractive_history_requires_explicit_mode(self):
        with self.assertRaisesRegex(BenchmarkError, "--resume or --fresh"):
            choose_resume([(None, self.report)], True, io.StringIO(), self.warning)
        self.assertFalse(choose_resume([], False, io.StringIO(), self.warning))

    def test_interactive_options_preserve_mode_prompt(self):
        with patch("local_bench.cli.run", return_value=0) as run, patch("local_bench.cli.sys.stdin.isatty", return_value=True):
            main([])
            self.assertTrue(run.call_args.args[0].prompt_for_mode)
            for options in (["--no-ui"], ["--download-workers", "1"], ["--model", "qwen3:*"], ["--publish"]):
                with self.subTest(options=options):
                    main(options)
                    self.assertTrue(run.call_args.args[0].prompt_for_mode)
            for mode in ("--resume", "--fresh", "--plan", "--publish-only"):
                with self.subTest(mode=mode):
                    main([mode])
                    self.assertFalse(run.call_args.args[0].prompt_for_mode)

    def test_noninteractive_explicit_options_keep_existing_behavior(self):
        with patch("local_bench.cli.run", return_value=0) as run, patch("local_bench.cli.sys.stdin.isatty", return_value=False):
            main(["--download-workers", "1"])
            self.assertFalse(run.call_args.args[0].prompt_for_mode)


class ResumeLifecycleCase(unittest.TestCase):
    setUp = test_runner.LifecycleCase.setUp
    run_fake = test_runner.LifecycleCase.run_fake

    def test_resume_skips_download_and_inference_and_preserves_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.run_fake(root)
            path = next((root / "results").rglob("results.json"))
            report = json.loads(path.read_text())
            catalog = load_catalog(root / "models.json")
            report["models"][0]["resolved_manifest_sha256"] = catalog["models"][0]["provenance"]["observed_manifest_sha256_prefix"] + "a" * 52
            path.write_text(json.dumps(report))
            test_runner.FakeEngine.request_count = 0
            self.run_fake(root, ("--resume",))
            latest = max((root / "results").rglob("results.json"), key=lambda item: item.parent.name)
            resumed = json.loads(latest.read_text())
            self.assertEqual(test_runner.FakeEngine.request_count, 0)
            self.assertIn("reused_from", resumed["models"][0])
            self.assertEqual(resumed["models"][0]["profiles"], report["models"][0]["profiles"])

    def test_fresh_does_not_reuse_previous_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.run_fake(root)
            test_runner.FakeEngine.request_count = 0
            self.run_fake(root, ("--fresh",))
            self.assertEqual(test_runner.FakeEngine.request_count, 13)
