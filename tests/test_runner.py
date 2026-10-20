import contextlib
import copy
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from local_bench.cli import main
from local_bench.config import BenchmarkError, SafetyError, load_catalog, validate_catalog
from local_bench.metrics import aggregate, duration_seconds, parse_metrics
from local_bench.processes import CommandRunner
from local_bench.registry import MANIFEST_TYPE, Manifest, Registry, validate_manifest
from local_bench.reports import publish
from local_bench.safety import Guard, Volume, disk_reason, memory_reason
from local_bench.system import Snapshot

ROOT = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3


class CatalogCase(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(ROOT / "models.json")
        self.model = copy.deepcopy(self.catalog["models"][0])
        self.policy = self.catalog["policy"]

    def test_current_catalog(self):
        self.assertEqual(len(self.catalog["models"]), 63)

    def test_unsupported_version(self):
        self.catalog["schema_version"] = "2.0.0"
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_reject_nonfinite_capacity(self):
        self.model["resources"]["download_bytes_upper_bound"] = float("nan")
        self.catalog["models"] = [self.model]
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_reject_parallel_requests(self):
        self.policy["execution"]["max_parallel_requests"] = 2
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_reject_environment_concurrency_mismatch(self):
        self.catalog["engine"]["server_environment"]["OLLAMA_NUM_PARALLEL"] = "4"
        with self.assertRaisesRegex(BenchmarkError, "environment conflicts"):
            validate_catalog(self.catalog)

    def test_reject_changed_context(self):
        self.catalog["benchmark"]["options"]["num_ctx"] = 131072
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_reject_duplicate_model(self):
        self.catalog["models"].append(self.model)
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_reject_foreign_registry(self):
        self.catalog["models"][0]["provenance"]["manifest_url"] = "https://example.com/weights"
        with self.assertRaises(BenchmarkError):
            validate_catalog(self.catalog)

    def test_low_available_memory(self):
        self.assertEqual(memory_reason(self.model, self.policy, Snapshot(16*GIB, GIB, "normal", 0)), "insufficient_available_memory")

    def test_memory_pressure(self):
        self.assertEqual(memory_reason(self.model, self.policy, Snapshot(64*GIB, 60*GIB, "warning", 0)), "memory_pressure_warning")

    def test_physical_memory_is_not_swap_capacity(self):
        large = next(model for model in self.catalog["models"] if model["ollama_tag"] == "gpt-oss:120b")
        self.assertEqual(memory_reason(large, self.policy, Snapshot(64*GIB, 60*GIB, "normal", 200*GIB)), "physical_memory_below_model_minimum")

    def test_resident_memory_credit(self):
        snapshot = Snapshot(16*GIB, 3*GIB, "normal", 0)
        self.assertIsNotNone(memory_reason(self.model, self.policy, snapshot))
        self.assertIsNone(memory_reason(self.model, self.policy, snapshot, 3*GIB))

    def test_metal_limit(self):
        self.assertEqual(memory_reason(self.model, self.policy, Snapshot(64*GIB, 60*GIB, "normal", 0, GIB)), "model_exceeds_metal_working_set")

    def test_same_volume_budgets_are_added(self):
        paths = {name: Path("/tmp") for name in ("model_store", "temporary_directory", "results_directory", "installer_cache")}
        payload = self.model["resources"]["download_bytes_upper_bound"]
        free = self.policy["disk"]["reserve_bytes"] + 3*payload + 3*GIB - 1
        provider = lambda path: Volume(1, path, 100*GIB, free)
        self.assertIsNotNone(disk_reason(self.model, self.policy, paths, volume_provider=provider))

    def test_disk_percentage_reserve(self):
        paths = {name: Path("/tmp") for name in ("model_store", "temporary_directory", "results_directory", "installer_cache")}
        provider = lambda path: Volume(1, path, 1000*GIB, 99*GIB)
        self.assertIsNotNone(disk_reason(self.model, self.policy, paths, admission=False, volume_provider=provider))

    def test_manifest_layer_accounting(self):
        document = {"schemaVersion": 2, "mediaType": MANIFEST_TYPE,
                    "config": {"size": 30, "digest": "sha256:" + "a"*64},
                    "layers": [{"size": 100, "digest": "sha256:" + "b"*64, "mediaType": "application/vnd.ollama.image.model"},
                               {"size": 20, "digest": "sha256:" + "c"*64, "mediaType": "application/vnd.ollama.image.projector"}]}
        raw = json.dumps(document).encode()
        self.model["provenance"]["observed_manifest_sha256_prefix"] = hashlib.sha256(raw).hexdigest()[:12]
        self.assertEqual(validate_manifest(raw, self.model, self.policy, {"model_format": "gguf"}).payload_bytes, 150)

    def test_manifest_digest_drift(self):
        with self.assertRaisesRegex(BenchmarkError, "tag_digest_changed"):
            validate_manifest(b"{}", self.model, self.policy, {})

    def test_non_object_config_is_rejected(self):
        raw = b"{}"
        self.model["provenance"]["observed_manifest_sha256_prefix"] = hashlib.sha256(raw).hexdigest()[:12]
        with self.assertRaisesRegex(BenchmarkError, "JSON objects"):
            validate_manifest(raw, self.model, self.policy, [])

    def test_non_gguf_rejected(self):
        raw = json.dumps({"schemaVersion": 2, "mediaType": MANIFEST_TYPE,
                          "config": {"size": 1, "digest": "sha256:" + "a"*64},
                          "layers": [{"size": 1, "digest": "sha256:" + "b"*64}]}).encode()
        self.model["provenance"]["observed_manifest_sha256_prefix"] = hashlib.sha256(raw).hexdigest()[:12]
        with self.assertRaisesRegex(BenchmarkError, "not a local GGUF"):
            validate_manifest(raw, self.model, self.policy, {"model_format": "safetensors"})

    def test_registry_reads_are_bounded(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, maximum):
                return b"x" * maximum

        registry = Registry(self.policy)
        with patch.object(registry.opener, "open", return_value=Response()):
            with self.assertRaisesRegex(BenchmarkError, "byte limit"):
                registry.fetch("https://registry.ollama.ai/test", 64)

    def test_watchdog_aborts_on_swap_growth(self):
        class Telemetry:
            snapshot_value = Snapshot(64*GIB, 60*GIB, "normal", 0)

            def snapshot(self):
                return self.snapshot_value

        telemetry = Telemetry()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {name: root for name in ("model_store", "temporary_directory", "results_directory", "installer_cache")}
            guard = Guard(telemetry, self.model, self.policy, paths, root, root, lambda: [])
            telemetry.snapshot_value = Snapshot(64*GIB, 60*GIB, "normal", 128*1024*1024)
            with self.assertRaisesRegex(SafetyError, "swap_growth"):
                guard.check()


class MetricsCase(unittest.TestCase):
    def test_go_durations(self):
        self.assertAlmostEqual(duration_seconds("1m2.5s"), 62.5)
        self.assertAlmostEqual(duration_seconds("250µs"), 0.00025)
        self.assertIsNone(duration_seconds("0s"))
        self.assertIsNone(duration_seconds("invalid"))

    def test_cached_prompt_metrics(self):
        result = parse_metrics("prompt eval count: 20 token(s)\nprompt eval cached: 5 token(s)\nprompt eval duration: 500ms\neval count: 10 token(s)\neval duration: 250ms\n", 1)
        self.assertEqual(result["generation_tokens_per_second"], 40)
        self.assertEqual(result["prompt_eval_tokens_per_second"], 30)

    def test_missing_metrics_do_not_crash(self):
        result = parse_metrics("eval count: 2 token(s)\neval duration: 0s\n", 1)
        self.assertIsNone(result["generation_tokens_per_second"])
        self.assertIn("generation_tokens_per_second", result["missing_metric_reasons"])

    def test_weighted_aggregation(self):
        first = parse_metrics("eval count: 10 token(s)\neval duration: 1s\n", 2)
        second = parse_metrics("eval count: 10 token(s)\neval duration: 2s\n", 3)
        combined = aggregate([{"metrics": first}, {"metrics": second}])
        self.assertAlmostEqual(combined["generation_tokens_per_second"], 20/3)
        self.assertEqual(combined["end_to_end_tokens_per_second"], 4)


class ProcessCase(unittest.TestCase):
    def setUp(self):
        self.policy = load_catalog(ROOT / "models.json")["policy"]
        self.children = patch("psutil.Process.children", return_value=[])
        self.children.start()
        self.addCleanup(self.children.stop)

    def test_command_timeout_cleans_owned_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            with self.assertRaisesRegex(SafetyError, "command_timeout"):
                runner.run([sys.executable, "-c", "import time; time.sleep(30)"], os.environ.copy(), 0.1)
            self.assertIsNone(runner.active)

    def test_output_limit_cleans_owned_process(self):
        self.policy["execution"]["maximum_captured_output_bytes_per_request"] = 100
        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            with self.assertRaisesRegex(SafetyError, "output_limit"):
                runner.run([sys.executable, "-c", "print('x'*1000)"], os.environ.copy(), 5)
            self.assertIsNone(runner.active)

    def test_command_failure_is_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            with self.assertRaisesRegex(BenchmarkError, "exited 3"):
                runner.run([sys.executable, "-c", "import sys; print('bad',file=sys.stderr); sys.exit(3)"], os.environ.copy(), 5)

    def test_spawn_failure_reaps_process(self):
        import subprocess

        children = []
        real_popen = subprocess.Popen

        def capture(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child

        with tempfile.TemporaryDirectory() as temporary:
            runner = CommandRunner(self.policy, temporary, lambda *args: None)
            with patch("psutil.Process.children", side_effect=PermissionError("telemetry denied")), patch("local_bench.processes.subprocess.Popen", side_effect=capture):
                with self.assertRaisesRegex(SafetyError, "track owned process"):
                    runner.run([sys.executable, "-c", "import time; time.sleep(30)"], os.environ.copy(), 5)
            self.assertIsNotNone(children[0].poll())
            self.assertTrue(children[0].stdout.closed)


class FakeTelemetry:
    def snapshot(self):
        return Snapshot(64*GIB, 60*GIB, "normal", 0)

    def specs(self):
        return {"os": "Darwin", "architecture": "arm64", "model": "test-mac", "memory": {"physical": 64*GIB}}

    def footprint(self, process):
        return 0


class FakeEngine:
    cleaned = False
    stopped = False
    request_count = 0
    fail_request = False

    def __init__(self, catalog, commands, workspace, result_dir):
        self.workspace = workspace
        self.store = workspace / "models"
        self.store.mkdir()
        self.paths = {name: workspace for name in ("model_store", "temporary_directory", "results_directory", "installer_cache")}
        self.version = "test-ollama"

    def install(self):
        pass

    def start(self):
        pass

    def pull(self, *args):
        pass

    def create_alias(self, model, probe=False):
        return "probe" if probe else "benchmark"

    def inspect(self, alias, expected):
        return expected

    def request(self, alias, prompt, first_load=False):
        type(self).request_count += 1
        if self.fail_request:
            raise SafetyError("simulated_guard_abort")
        count = 1 if alias == "probe" else 16
        return parse_metrics(f"prompt eval count: 32 token(s)\neval count: {count} token(s)\neval duration: 1s\n", 1.5)

    def unload(self, alias):
        pass

    def clear_model(self, *args):
        type(self).cleaned = True

    def stop_server(self):
        type(self).stopped = True


class LifecycleCase(unittest.TestCase):
    def setUp(self):
        FakeEngine.cleaned = FakeEngine.stopped = FakeEngine.fail_request = False
        FakeEngine.request_count = 0

    def run_fake(self, root, extra=()):
        catalog = load_catalog(ROOT / "models.json")
        catalog["models"] = [catalog["models"][0]]
        catalog_path = root / "models.json"
        catalog_path.write_text(json.dumps(catalog))
        manifest = Manifest("a"*64, {}, 300, "Q8_0")
        with patch("local_bench.cli.MacTelemetry", FakeTelemetry), patch("local_bench.cli.Ollama", FakeEngine), patch("local_bench.cli.Registry.resolve", return_value=manifest), contextlib.redirect_stdout(io.StringIO()):
            code = main(["--models-file", str(catalog_path), "--output-dir", str(root / "results"), "--work-dir", str(root / "work"), "--no-ui", *extra])
        report_path = next((root / "results").rglob("results.json"))
        return code, json.loads(report_path.read_text())

    def test_plan_does_not_download_or_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, report = self.run_fake(Path(temporary), ("--plan",))
            self.assertEqual(code, 0)
            self.assertEqual(report["models"][0]["status"], "planned")
            self.assertEqual(FakeEngine.request_count, 0)

    def test_probes_warmups_and_measured_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            code, report = self.run_fake(Path(temporary))
            self.assertEqual(code, 0)
            model = report["models"][0]
            self.assertEqual(model["status"], "completed")
            self.assertEqual(len(model["probes"]), 3)
            self.assertEqual(len(model["warmups"]), 1)
            self.assertEqual([profile["metrics"]["requests"] for profile in model["profiles"]], [1, 8])
            self.assertEqual(FakeEngine.request_count, 13)
            self.assertTrue(FakeEngine.cleaned and FakeEngine.stopped)
            self.assertFalse(list((Path(temporary) / "work").glob("run-*")))

    def test_abort_cleans_owned_artifacts(self):
        FakeEngine.fail_request = True
        with tempfile.TemporaryDirectory() as temporary:
            code, report = self.run_fake(Path(temporary))
            self.assertEqual(report["models"][0]["skip_or_failure_reason"], "simulated_guard_abort")
            self.assertTrue(FakeEngine.cleaned and FakeEngine.stopped)
            self.assertFalse(list((Path(temporary) / "work").glob("run-*")))


class PublicationCase(unittest.TestCase):
    def test_invalid_markers_leave_readme_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("manual content")
            directory = root / "benchmarks" / "runs" / "device" / "run"
            directory.mkdir(parents=True)
            with self.assertRaisesRegex(BenchmarkError, "markers"):
                publish(root, directory, {"status": "completed", "models": [{"status": "completed"}]})
            self.assertEqual((root / "README.md").read_text(), "manual content")

    def test_publish_preserves_manual_sections(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("Intro\n<!-- BENCHMARKS:START -->\nold\n<!-- BENCHMARKS:END -->\nFooter\n")
            directory = root / "benchmarks" / "runs" / "device" / "run"
            directory.mkdir(parents=True)
            (root / "benchmarks" / "README.md").write_text("# Results\n\n## Run Reports\n")
            report = {"status": "completed", "run_id": "run", "device_id": "device", "models": [{"status": "completed"}]}
            publish(root, directory, report)
            result = (root / "README.md").read_text()
            self.assertTrue(result.startswith("Intro\n"))
            self.assertTrue(result.endswith("\nFooter\n"))
            self.assertIn("benchmarks/runs/device/run/report.md", result)


if __name__ == "__main__":
    unittest.main()
