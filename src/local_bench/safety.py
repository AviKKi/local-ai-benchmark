import math
import os
from dataclasses import dataclass
from pathlib import Path

from .config import SafetyError


def memory_budget(model, policy):
    return math.ceil(model["resources"]["estimated_peak_unified_memory_bytes"] * policy["memory"]["estimate_multiplier"])


def memory_reason(model, policy, snapshot, resident_credit=0):
    memory = policy["memory"]
    budget = memory_budget(model, policy)
    if snapshot.physical < model["resources"]["minimum_physical_memory_bytes"]:
        return "physical_memory_below_model_minimum"
    if budget > snapshot.physical * memory["maximum_physical_memory_fraction"]:
        return "model_exceeds_physical_memory_fraction"
    if budget + memory["os_reserve_bytes"] > snapshot.physical:
        return "insufficient_os_memory_reserve"
    if snapshot.pressure != memory["admit_only_when_memory_pressure"]:
        return f"memory_pressure_{snapshot.pressure}"
    incremental = max(0, budget - min(budget, resident_credit))
    if incremental + memory["minimum_available_after_admission_bytes"] > snapshot.available:
        return "insufficient_available_memory"
    if snapshot.metal_recommended is not None and budget > snapshot.metal_recommended * memory["maximum_metal_working_set_fraction_if_reported"]:
        return "model_exceeds_metal_working_set"
    return None


@dataclass
class Volume:
    device: int
    path: Path
    total: int
    free: int


def volume_at(path):
    path = Path(path).resolve()
    while not path.exists():
        path = path.parent
    info = os.statvfs(path)
    return Volume(path.stat().st_dev, path, info.f_blocks * info.f_frsize, info.f_bavail * info.f_frsize)


def disk_reason(model, policy, paths, admission=True, volume_provider=volume_at):
    disk = policy["disk"]
    payload = model["resources"]["download_bytes_upper_bound"]
    volumes = {role: volume_provider(path) for role, path in paths.items()}
    charges = {"model_store": payload * disk["download_and_temporary_multiplier"],
               "installer_cache": disk["installer_budget_bytes"],
               "installer_destination": disk["installer_budget_bytes"],
               "results_directory": disk["maximum_total_results_bytes"], "temporary_directory": 0}
    if volumes["temporary_directory"].device != volumes["model_store"].device:
        charges["temporary_directory"] = payload
    grouped = {}
    for role, volume in volumes.items():
        entry = grouped.setdefault(volume.device, [volume, 0])
        entry[1] += charges[role] if admission else 0
    for volume, charge in grouped.values():
        reserve = max(disk["reserve_bytes"], math.ceil(volume.total * disk["reserve_volume_fraction"]))
        if volume.free < reserve + charge:
            return f"insufficient_disk_space:{volume.path} (free={volume.free}, required={reserve + charge})"
    return None


def tree_bytes(root):
    total = 0
    for current, directories, files in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories if not (Path(current) / name).is_symlink()]
        for name in files:
            path = Path(current) / name
            try:
                total += path.lstat().st_size
            except FileNotFoundError:
                continue
    return total


class Guard:
    def __init__(self, telemetry, model, policy, paths, result_dir, model_store, owned_processes, on_sample=None):
        self.telemetry, self.model, self.policy = telemetry, model, policy
        self.paths, self.result_dir, self.model_store = paths, result_dir, model_store
        self.owned_processes = owned_processes
        self.on_sample = on_sample or (lambda sample: None)
        self.model_baseline = telemetry.snapshot()
        self.stage_baseline = self.model_baseline
        self.peak_footprint = 0
        self.peak_system_drop = 0
        self.peak_cpu_percent = 0.0
        self.maximum_swap_growth = 0
        self.minimum_available = self.model_baseline.available
        self.peak_pressure = "normal"
        self.cpu_previous = {}
        self.last_cpu_time = None

    def admit(self, resident=False, disk=True):
        credit = self.process_footprint() if resident else 0
        reason = memory_reason(self.model, self.policy, self.telemetry.snapshot(), credit)
        if not reason and disk:
            reason = disk_reason(self.model, self.policy, self.paths)
        if reason:
            raise SafetyError(reason)

    def begin_stage(self):
        self.stage_baseline = self.telemetry.snapshot()
        self.check()

    def process_footprint(self):
        total = 0
        for process in self.owned_processes():
            try:
                total += self.telemetry.footprint(process)
            except Exception:
                if process.is_running():
                    raise
        return total

    def check(self):
        import time

        watchdog = self.policy["watchdog"]
        snapshot = self.telemetry.snapshot()
        self.minimum_available = min(self.minimum_available, snapshot.available)
        footprint = self.process_footprint()
        self.peak_footprint = max(self.peak_footprint, footprint)
        drop = max(0, self.model_baseline.available - snapshot.available)
        self.peak_system_drop = max(self.peak_system_drop, drop)
        growth = max(0, snapshot.swap_used - self.stage_baseline.swap_used)
        self.maximum_swap_growth = max(self.maximum_swap_growth, growth)
        now, cpu_total = time.monotonic(), 0.0
        for process in self.owned_processes():
            try:
                times = process.cpu_times()
                current = times.user + times.system
                previous = self.cpu_previous.get(process.pid, current)
                cpu_total += max(0, current - previous)
                self.cpu_previous[process.pid] = current
            except Exception:
                if process.is_running():
                    raise SafetyError("CPU telemetry unavailable for owned process")
        if self.last_cpu_time is not None and now > self.last_cpu_time:
            self.peak_cpu_percent = max(self.peak_cpu_percent, cpu_total / (now - self.last_cpu_time) * 100)
        self.last_cpu_time = now
        if snapshot.pressure in watchdog["abort_on_memory_pressure"]:
            self.peak_pressure = snapshot.pressure
            raise SafetyError(f"watchdog:memory_pressure_{snapshot.pressure}")
        if snapshot.available < watchdog["minimum_available_memory_bytes"]:
            raise SafetyError("watchdog:available_memory_below_reserve")
        if growth > watchdog["maximum_swap_growth_bytes"]:
            raise SafetyError("watchdog:swap_growth")
        if max(footprint, drop) > memory_budget(self.model, self.policy):
            raise SafetyError("watchdog:model_memory_budget_exceeded")
        reason = disk_reason(self.model, self.policy, self.paths, admission=False)
        if reason:
            raise SafetyError(f"watchdog:{reason}")
        if tree_bytes(self.result_dir) > self.policy["disk"]["maximum_total_results_bytes"]:
            raise SafetyError("watchdog:results_budget_exceeded")
        staging_limit = self.model["resources"]["download_bytes_upper_bound"] * self.policy["disk"]["download_and_temporary_multiplier"]
        if tree_bytes(self.model_store) > staging_limit + self.policy["disk"]["maximum_manifest_bytes"] * 4:
            raise SafetyError("watchdog:download_upper_bound_exceeded")
        self.on_sample({"available": snapshot.available, "footprint": footprint, "pressure": snapshot.pressure})

    def metrics(self):
        return {
            "peak_runner_and_server_memory_bytes": self.peak_footprint,
            "peak_system_available_drop_bytes": self.peak_system_drop,
            "minimum_available_memory_bytes": self.minimum_available,
            "system_memory_pressure": self.peak_pressure,
            "swap_growth_bytes": self.maximum_swap_growth,
            "peak_cpu_percent_one_core_is_100": self.peak_cpu_percent,
            "gpu_usage_percent": None,
            "gpu_usage_missing_reason": "GPU utilization requires privileged/platform-specific telemetry; not collected",
            "memory_method": "sum of owned processes' macOS physical footprints; guard also checks system available-memory drop without adding the two",
        }
