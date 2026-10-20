import os
import selectors
import signal
import subprocess
import time
import re
from contextlib import contextmanager
from dataclasses import dataclass

import psutil

from .config import BenchmarkError, CleanupError, SafetyError


@contextmanager
def cleanup_signals():
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        for number in previous:
            signal.signal(number, signal.SIG_IGN)
        yield
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


class OwnedProcess:
    def __init__(self, args, env, cwd, stderr=subprocess.PIPE):
        self.child = subprocess.Popen(args, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=stderr, start_new_session=True)
        self.known = {}
        try:
            self.refresh()
        except BaseException:
            if self.child.poll() is None:
                try:
                    os.killpg(self.child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.child.wait(timeout=5)
            for stream in (self.child.stdout, self.child.stderr):
                if stream:
                    stream.close()
            raise

    def refresh(self):
        try:
            root = psutil.Process(self.child.pid)
            if self.child.poll() is None:
                self.known.setdefault(root.pid, root)
                for process in root.children(recursive=True):
                    self.known.setdefault(process.pid, process)
        except psutil.NoSuchProcess:
            pass
        except (psutil.Error, OSError) as error:
            raise SafetyError(f"Cannot track owned process tree: {error}") from error
        live = []
        for process in self.known.values():
            try:
                if process.is_running() and process.status() != psutil.STATUS_ZOMBIE:
                    live.append(process)
            except psutil.NoSuchProcess:
                continue
        return live

    def stop(self, grace):
        tracking_error = None
        try:
            processes = self.refresh()
        except (SafetyError, psutil.Error, OSError) as error:
            processes = list(self.known.values())
            tracking_error = error
        if self.child.poll() is None:
            try:
                if os.getpgid(self.child.pid) != self.child.pid:
                    raise CleanupError("Owned process lost its dedicated process group")
                os.killpg(self.child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in processes:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(processes, timeout=grace)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(alive, timeout=grace)
        try:
            self.child.wait(timeout=grace)
        except subprocess.TimeoutExpired as error:
            raise CleanupError("Owned command/server did not exit") from error
        if alive:
            raise CleanupError("Owned child processes survived cleanup")
        if tracking_error:
            raise CleanupError(f"Process tracking failed during teardown; owned group stopped: {tracking_error}")


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    seconds: float


class CommandRunner:
    def __init__(self, policy, cwd, event):
        self.policy, self.cwd, self.event = policy, cwd, event
        self.active = None
        self.server = None
        self.guard = None

    def processes(self):
        result = {}
        for owned in (self.server, self.active):
            if owned is not None:
                for process in owned.refresh():
                    result[process.pid] = process
        return list(result.values())

    def stop_all(self):
        grace = self.policy["execution"]["termination_grace_seconds"]
        for name in ("active", "server"):
            owned = getattr(self, name)
            if owned is not None:
                owned.stop(grace)
                setattr(self, name, None)

    def run(self, args, env, timeout, check=True):
        if self.guard:
            self.guard.begin_stage()
        self.event("command", " ".join(args[:3]))
        started = time.monotonic()
        self.active = OwnedProcess(args, env, self.cwd)
        owned = self.active
        output = {"stdout": bytearray(), "stderr": bytearray()}
        limit = self.policy["execution"]["maximum_captured_output_bytes_per_request"]
        interval = self.policy["watchdog"]["poll_interval_milliseconds"] / 1000
        next_check = started
        last_percentage = -1
        selector = selectors.DefaultSelector()
        try:
            for name in output:
                stream = getattr(self.active.child, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map() or self.active.child.poll() is None:
                now = time.monotonic()
                if now - started > timeout:
                    raise SafetyError(f"command_timeout:{args[1] if len(args) > 1 else args[0]}")
                if now >= next_check:
                    if self.guard:
                        self.guard.check()
                    next_check = now + interval
                for key, _ in selector.select(min(interval, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        output[key.data].extend(chunk)
                        if sum(map(len, output.values())) > limit:
                            raise SafetyError("command_output_limit_exceeded")
                        if len(args) > 1 and args[1] == "pull":
                            percentages = re.findall(rb"\b(\d{1,3})%", output[key.data][-4096:])
                            if percentages:
                                percentage = int(percentages[-1]) // 10 * 10
                                if 0 <= percentage <= 100 and percentage != last_percentage:
                                    self.event("download", f"{args[-1]} · current layer {percentage}%")
                                    last_percentage = percentage
            returncode = self.active.child.wait()
            result = CommandResult(*(output[name].decode("utf-8", errors="replace") for name in ("stdout", "stderr")), time.monotonic() - started)
            if self.guard:
                self.guard.check()
            if check and returncode:
                detail = result.stderr.strip()[-1500:]
                raise BenchmarkError(f"Command exited {returncode}: {detail}")
            return result
        except BaseException:
            with cleanup_signals():
                self.stop_all()
            raise
        finally:
            selector.close()
            for name in output:
                getattr(owned.child, name).close()
            self.active = None
