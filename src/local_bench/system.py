import ctypes
import os
import platform
from dataclasses import asdict, dataclass

import psutil

from .config import SafetyError
from .processes import process_is_live


class RUsageInfo(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_ubyte * 16)] + [
        (name, ctypes.c_uint64) for name in (
            "user_time", "system_time", "idle_wakeups", "interrupt_wakeups", "pageins",
            "wired_size", "resident_size", "physical_footprint", "start_time", "exit_time",
        )
    ]


@dataclass
class Snapshot:
    physical: int
    available: int
    pressure: str
    swap_used: int
    metal_recommended: int | None = None


class MacTelemetry:
    def __init__(self):
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise SafetyError("Only Apple Silicon macOS is supported")
        self.libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        self.libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        self.libc.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        self.libc.sysctlbyname.restype = ctypes.c_int
        self.libproc.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        self.libproc.proc_pid_rusage.restype = ctypes.c_int

    def sysctl(self, name):
        length = ctypes.c_size_t()
        if self.libc.sysctlbyname(name.encode(), None, ctypes.byref(length), None, 0):
            raise SafetyError(f"Cannot read required sysctl {name}: {os.strerror(ctypes.get_errno())}")
        buffer = ctypes.create_string_buffer(length.value)
        if self.libc.sysctlbyname(name.encode(), buffer, ctypes.byref(length), None, 0):
            raise SafetyError(f"Cannot read required sysctl {name}")
        return buffer.raw[:length.value]

    def text(self, name):
        try:
            return self.sysctl(name).rstrip(b"\0").decode()
        except SafetyError:
            return None

    def snapshot(self):
        try:
            memory = psutil.virtual_memory()
            free_and_inactive = memory.free + memory.inactive
            pressure_value = int.from_bytes(self.sysctl("kern.memorystatus_vm_pressure_level"), "little")
            pressure = {1: "normal", 2: "warning", 4: "critical"}.get(pressure_value)
            if pressure is None:
                raise SafetyError(f"Unknown macOS memory-pressure value: {pressure_value}")
            return Snapshot(memory.total, min(memory.available, free_and_inactive), pressure, psutil.swap_memory().used)
        except (OSError, psutil.Error, AttributeError) as error:
            raise SafetyError(f"Required memory telemetry unavailable: {error}") from error

    def footprint(self, process):
        info = RUsageInfo()
        if self.libproc.proc_pid_rusage(process.pid, 0, ctypes.byref(info)):
            if not process_is_live(process):
                return 0
            raise SafetyError(f"Cannot read physical footprint of owned process {process.pid}")
        return info.physical_footprint

    def specs(self):
        return {
            "os": platform.system(), "os_version": platform.mac_ver()[0],
            "architecture": platform.machine(), "model": self.text("hw.model"),
            "chip": self.text("machdep.cpu.brand_string"),
            "logical_cpu_count": psutil.cpu_count(), "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory": asdict(self.snapshot()), "page_size_bytes": os.sysconf("SC_PAGE_SIZE"),
            "metal_recommended_working_set_bytes": None,
            "metal_working_set_note": "Not exposed by this telemetry provider; the optional catalog limit is not applied.",
        }
