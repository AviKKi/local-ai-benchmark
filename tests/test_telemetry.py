import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import psutil

from local_bench.config import SafetyError, load_catalog
from local_bench.safety import Guard, initialize_memory_cap
from local_bench.system import MacTelemetry, Snapshot


ROOT = Path(__file__).resolve().parents[1]
GIB = 1024 ** 3


class TelemetryCase(unittest.TestCase):
    def setUp(self):
        catalog = load_catalog(ROOT / "models.json")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.process = Mock(pid=12345)
        self.process.is_running.return_value = True
        self.process.status.return_value = psutil.STATUS_RUNNING
        self.process.cpu_times.return_value = SimpleNamespace(user=1.0, system=0.5)
        self.telemetry = Mock()
        self.telemetry.snapshot.return_value = Snapshot(64 * GIB, 60 * GIB, "normal", 0)
        initialize_memory_cap(catalog["policy"], self.telemetry.snapshot())
        self.telemetry.footprint.return_value = 100
        self.guard = Guard(self.telemetry, catalog["models"][0], catalog["policy"], {}, root, root,
                           lambda: [self.process])
        disk = patch("local_bench.safety.disk_reason", return_value=None)
        disk.start()
        self.addCleanup(disk.stop)

    def test_available_memory_includes_reclaimable_without_double_counting(self):
        telemetry = MacTelemetry.__new__(MacTelemetry)
        telemetry.sysctl = Mock(return_value=(1).to_bytes(4, 'little'))
        memory = SimpleNamespace(total=64*GIB, available=57*GIB, free=50*GIB, inactive=3*GIB)
        with patch("local_bench.system.psutil.virtual_memory", return_value=memory), patch("local_bench.system.psutil.swap_memory", return_value=SimpleNamespace(used=0)):
            self.assertEqual(telemetry.snapshot().available, 57*GIB)

    def test_watchdog_enforces_frozen_cap_and_live_buffer(self):
        self.guard.policy["run_memory"]["cap_bytes"] = 512
        self.telemetry.footprint.return_value = 513
        with self.assertRaisesRegex(SafetyError, "model_memory_budget_exceeded"):
            self.guard.check()
        self.telemetry.footprint.return_value = 0
        self.telemetry.snapshot.return_value = Snapshot(64*GIB, GIB, "normal", 0)
        with self.assertRaisesRegex(SafetyError, "available_memory_below_reserve"):
            self.guard.check()

    def test_cpu_zombie_after_process_discovery(self):
        self.process.cpu_times.side_effect = psutil.ZombieProcess(self.process.pid)
        self.guard.check()

    def test_cpu_process_disappears_after_discovery(self):
        self.process.cpu_times.side_effect = psutil.NoSuchProcess(self.process.pid)
        self.guard.check()

    def test_cpu_access_denied_during_zombie_transition(self):
        self.process.cpu_times.side_effect = psutil.AccessDenied(self.process.pid)
        self.process.status.return_value = psutil.STATUS_ZOMBIE
        self.guard.check()

    def test_process_disappears_during_liveness_check(self):
        self.process.cpu_times.side_effect = psutil.AccessDenied(self.process.pid)
        self.process.status.side_effect = psutil.NoSuchProcess(self.process.pid)
        self.guard.check()

    def test_zombie_does_not_bypass_memory_pressure_check(self):
        self.process.cpu_times.side_effect = psutil.ZombieProcess(self.process.pid)
        self.telemetry.snapshot.return_value = Snapshot(64 * GIB, 60 * GIB, "critical", 0)
        with self.assertRaisesRegex(SafetyError, "memory_pressure_critical"):
            self.guard.check()

    def test_cpu_access_denied_for_live_process_still_aborts(self):
        error = psutil.AccessDenied(self.process.pid)
        self.process.cpu_times.side_effect = error
        with self.assertRaisesRegex(SafetyError, "12345.*AccessDenied") as raised:
            self.guard.check()
        self.assertIs(raised.exception.__cause__, error)

    def test_cpu_unreadable_liveness_still_aborts(self):
        self.process.cpu_times.side_effect = psutil.AccessDenied(self.process.pid)
        self.process.status.side_effect = psutil.AccessDenied(self.process.pid)
        with self.assertRaises(SafetyError):
            self.guard.check()

    def test_cpu_measurement_remains_active(self):
        with patch("time.monotonic", side_effect=[10.0, 11.0]):
            self.guard.check()
            self.process.cpu_times.return_value = SimpleNamespace(user=2.0, system=0.5)
            self.guard.check()
        self.assertEqual(self.guard.peak_cpu_percent, 100.0)

    def test_footprint_zombie_after_discovery(self):
        self.telemetry.footprint.side_effect = SafetyError("process exited")
        self.process.status.return_value = psutil.STATUS_ZOMBIE
        self.assertEqual(self.guard.process_footprint(), 0)

    def test_footprint_live_process_error_still_aborts(self):
        self.telemetry.footprint.side_effect = SafetyError("footprint unavailable")
        with self.assertRaisesRegex(SafetyError, "footprint unavailable"):
            self.guard.process_footprint()

    def test_native_footprint_zombie_returns_zero(self):
        telemetry = MacTelemetry.__new__(MacTelemetry)
        telemetry.libproc = Mock()
        telemetry.libproc.proc_pid_rusage.return_value = -1
        self.process.status.return_value = psutil.STATUS_ZOMBIE
        self.assertEqual(telemetry.footprint(self.process), 0)

    def test_native_footprint_live_process_error_still_aborts(self):
        telemetry = MacTelemetry.__new__(MacTelemetry)
        telemetry.libproc = Mock()
        telemetry.libproc.proc_pid_rusage.return_value = -1
        with self.assertRaisesRegex(SafetyError, "physical footprint"):
            telemetry.footprint(self.process)
