import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "test-download-concurrency.sh"


class DownloadShellCase(unittest.TestCase):
    def test_shell_syntax_and_help(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True, capture_output=True)
        result = subprocess.run(["bash", str(SCRIPT), "--help"], check=True, capture_output=True, text=True)
        self.assertIn("1, 2, 4 and 6", result.stdout)

    def test_invalid_target_fails_before_any_network(self):
        result = subprocess.run(["bash", str(SCRIPT)], env=dict(os.environ, TARGET_PERCENT="100"),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Invalid TARGET_PERCENT", result.stderr)

    def run_stubbed(self, dry_run=False, free_kib=350000000, curl_script=None):
        if not shutil.which("jq"):
            self.skipTest("jq is required by the standalone shell experiment")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binaries = root / "bin"
            binaries.mkdir()
            fixtures = {
                "ollama": "exec sleep 30\n",
                "lsof": 'case " $* " in *" -p "*) exit 0;; *) exit 1;; esac\n',
                "df": f"printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\nfixture 400000000 1 {free_kib} 1%% /\\n'\n",
                "curl": curl_script or "printf '%s\\n' '{\"total\":6000000000,\"completed\":600000000}'\nexec sleep 30\n",
            }
            for name, source in fixtures.items():
                path = binaries / name
                path.write_text("#!/usr/bin/env bash\n" + source)
                path.chmod(0o755)
            environment = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}", WORK_ROOT=str(root / "work"),
                               MODELS_FILE=str(ROOT / "models.json"), TARGET_PERCENT="5", MAX_SECONDS="10", PORT="11436")
            result = subprocess.run(["bash", str(SCRIPT), *(["--dry-run"] if dry_run else [])],
                                    env=environment, capture_output=True, text=True, timeout=30)
            self.assertFalse(list((root / "work").glob("download-test.*")))
            return result

    def test_dry_run_only_checks_queue_and_cleans_workspace(self):
        result = self.run_stubbed(dry_run=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("full queue budget", result.stdout)
        for concurrency in (1, 2, 4, 6):
            self.assertIn(f"Concurrency {concurrency}: admitted", result.stdout)

    def test_low_disk_refuses_before_starting_server(self):
        result = self.run_stubbed(dry_run=True, free_kib=1000000)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Insufficient disk", result.stderr)

    def test_partial_transfer_comparison_with_no_real_network_or_models(self):
        result = self.run_stubbed()
        self.assertEqual(result.returncode, 0, result.stderr)
        for concurrency in (1, 2, 4, 6):
            self.assertIn(f"{concurrency}\tcompleted\t{concurrency * 600000000}", result.stdout)
        self.assertIn("single-download throughput", result.stdout)
        self.assertIn("Provisional sweet spot:", result.stdout)

    def test_unsafe_higher_levels_are_skipped_without_losing_lower_levels(self):
        result = self.run_stubbed(dry_run=True, free_kib=100000000)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Concurrency 1: admitted", result.stdout)
        self.assertIn("Concurrency 2: admitted", result.stdout)
        self.assertIn("SKIPPED: concurrency 6", result.stderr)

    def test_failed_transfer_is_not_a_successful_speed_measurement(self):
        result = self.run_stubbed(curl_script="echo 'simulated TLS timeout' >&2\nexit 22\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("simulated TLS timeout", result.stderr)
        self.assertNotIn("Provisional sweet spot:", result.stdout)
