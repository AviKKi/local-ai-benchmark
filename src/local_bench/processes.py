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


def process_is_live(process):
    try:
        return process.is_running() and process.status() not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD)
    except psutil.NoSuchProcess:
        return False


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
                if process_is_live(process):
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
    returncode: int = 0


def capture_output(output, stream, chunk, limit, tail=False):
    output[stream].extend(chunk)
    if tail:
        # Pull progress is a stream, not a response. Keep a bounded diagnostic
        # tail per stream while continuing to drain both pipes.
        capacity = max(1, limit // 2)
        if len(output[stream]) > capacity:
            del output[stream][:-capacity]
    elif sum(map(len, output.values())) > limit:
        raise SafetyError("command_output_limit_exceeded")


class CommandRunner:
    def __init__(self, policy, cwd, event):
        self.policy, self.cwd, self.event = policy, cwd, event
        self.active = None
        self.server = None
        self.guard = None
        self.downloads = []

    def processes(self):
        result = {}
        for owned in (self.server, self.active, *self.downloads):
            if owned is not None:
                for process in owned.refresh():
                    result[process.pid] = process
        return list(result.values())

    def stop_all(self):
        grace = self.policy["execution"]["termination_grace_seconds"]
        error = None
        for owned in self.downloads:
            try:
                owned.stop(grace)
            except (BenchmarkError, OSError, psutil.Error) as failure:
                error = error or failure
        self.downloads = []
        for name in ("active", "server"):
            owned = getattr(self, name)
            if owned is not None:
                try:
                    owned.stop(grace)
                except (BenchmarkError, OSError, psutil.Error) as failure:
                    error = error or failure
                finally:
                    setattr(self, name, None)
        if error:
            raise error

    def pull_many(self, arguments, env, timeout):
        if not 1 <= len(arguments) <= min(2, self.policy["execution"]["max_concurrent_downloads"]):
            raise BenchmarkError("Only one or two concurrent downloads are supported")
        if self.active or self.downloads or any(len(command) != 3 or command[1] != "pull" for command in arguments):
            raise BenchmarkError("Concurrent execution is restricted to isolated model pulls")
        if self.guard:
            self.guard.begin_stage()
        selector = selectors.DefaultSelector()
        states = []
        started = time.monotonic()
        interval = self.policy["watchdog"]["poll_interval_milliseconds"] / 1000
        next_check = started
        limit = self.policy["execution"]["maximum_captured_download_output_bytes"]
        try:
            for command in arguments:
                self.event("command", " ".join(command))
                owned = OwnedProcess(command, env, self.cwd)
                self.downloads.append(owned)
                state = {"owned": owned, "command": command, "output": {"stdout": bytearray(), "stderr": bytearray()},
                         "percentage": -1, "seconds": None}
                states.append(state)
                for name in state["output"]:
                    stream = getattr(owned.child, name)
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, (state, name))
            while selector.get_map() or any(state["owned"].child.poll() is None for state in states):
                now = time.monotonic()
                if now - started > timeout:
                    raise SafetyError("command_timeout:parallel_pull")
                if now >= next_check:
                    if self.guard:
                        self.guard.check()
                    next_check = now + interval
                for key, _ in selector.select(min(interval, 0.1)):
                    state, name = key.data
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        capture_output(state["output"], name, chunk, limit, tail=True)
                        percentages = re.findall(rb"\b(\d{1,3})%", state["output"][name][-4096:])
                        percentage = int(percentages[-1]) // 10 * 10 if percentages else -1
                        if 0 <= percentage <= 100 and percentage != state["percentage"]:
                            self.event("download", f"{state['command'][-1]} · current layer {percentage}% (paired downloads)")
                            state["percentage"] = percentage
                for state in states:
                    if state["seconds"] is None and state["owned"].child.poll() is not None:
                        state["seconds"] = time.monotonic() - started
            results = [CommandResult(*(state["output"][name].decode("utf-8", errors="replace") for name in ("stdout", "stderr")),
                                     state["seconds"], state["owned"].child.wait()) for state in states]
            for owned in self.downloads:
                owned.stop(self.policy["execution"]["termination_grace_seconds"])
            if self.guard:
                self.guard.check()
            return results
        except BaseException:
            with cleanup_signals():
                self.stop_all()
            raise
        finally:
            selector.close()
            for state in states:
                for name in state["output"]:
                    getattr(state["owned"].child, name).close()
            self.downloads = []

    def run(self, args, env, timeout, check=True):
        if self.guard:
            self.guard.begin_stage()
        self.event("command", " ".join(args[:3]))
        started = time.monotonic()
        self.active = OwnedProcess(args, env, self.cwd)
        owned = self.active
        output = {"stdout": bytearray(), "stderr": bytearray()}
        is_pull = len(args) > 1 and args[1] == "pull"
        limit = self.policy["execution"]["maximum_captured_download_output_bytes" if is_pull else "maximum_captured_output_bytes_per_request"]
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
                        capture_output(output, key.data, chunk, limit, tail=is_pull)
                        if is_pull:
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
