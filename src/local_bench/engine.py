import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import psutil

from .config import BenchmarkError, CleanupError, SafetyError, modelfile
from .metrics import ANSI, parse_metrics
from .processes import OwnedProcess


class Ollama:
    def __init__(self, catalog, commands, workspace, result_dir):
        self.catalog, self.commands = catalog, commands
        self.policy = catalog["policy"]
        self.workspace, self.result_dir = workspace, result_dir
        self.store = workspace / "models"
        self.store.mkdir()
        self.temporary = workspace / "tmp"
        self.temporary.mkdir()
        self.cache = workspace / "installer-cache"
        self.cache.mkdir()
        self.binary = shutil.which("ollama")
        brew = shutil.which("brew")
        self.install_destination = Path(brew).parent.parent if brew else Path("/opt/homebrew")
        self.version = None
        self.log_error = None
        self.log_thread = None
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("OLLAMA_") and key.upper() not in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}}
        self.env.update(catalog["engine"]["server_environment"])
        self.env["OLLAMA_MODELS"] = str(self.store.resolve())
        self.env.update({"TMPDIR": str(self.temporary.resolve()), "NO_PROXY": "127.0.0.1,localhost", "TERM": "dumb", "NO_COLOR": "1"})
        if self.env["OLLAMA_HOST"] != "127.0.0.1:11435":
            raise BenchmarkError("The owned server must use 127.0.0.1:11435")

    @property
    def paths(self):
        return {"model_store": self.store, "temporary_directory": self.temporary,
                "results_directory": self.result_dir, "installer_cache": self.cache,
                "installer_destination": self.install_destination}

    def cli(self, *arguments, timeout=None, check=True):
        if not self.binary:
            raise BenchmarkError("Ollama is not installed")
        return self.commands.run([self.binary, *arguments], self.env,
                                 timeout or self.policy["execution"]["request_timeout_seconds"], check)

    def install(self):
        if self.binary:
            return
        brew = shutil.which("brew")
        if not brew:
            raise BenchmarkError("Ollama is missing and Homebrew is unavailable. Install Homebrew, then rerun; or install Ollama manually.")
        environment = dict(os.environ, HOMEBREW_CACHE=str(self.cache.resolve()),
                           HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_INSTALL_CLEANUP="1",
                           TMPDIR=str(self.temporary.resolve()), HOMEBREW_TEMP=str(self.temporary.resolve()),
                           HOMEBREW_NO_ANALYTICS="1")
        prefix = self.commands.run([brew, "--prefix"], environment, 30).stdout.strip()
        if not prefix.startswith("/") or "\n" in prefix:
            raise BenchmarkError("Homebrew did not report a valid installation prefix")
        self.install_destination = Path(prefix)
        if self.commands.guard:
            self.commands.guard.paths = self.paths
            self.commands.guard.admit()
        self.commands.run([brew, "install", "ollama"], environment, self.policy["execution"]["download_timeout_seconds"])
        self.binary = shutil.which("ollama")
        if not self.binary:
            raise BenchmarkError("Homebrew completed but ollama is not on PATH")

    def _capture_server_log(self, stream):
        path = self.result_dir / "ollama.log"
        try:
            with path.open("ab") as output:
                total = path.stat().st_size
                while chunk := stream.read(4096):
                    total += len(chunk)
                    if total > min(16 * 1024 * 1024, self.policy["disk"]["maximum_total_results_bytes"] // 8):
                        self.log_error = "Owned server log exceeded its capture limit"
                        return
                    output.write(chunk)
                    output.flush()
        except OSError as error:
            self.log_error = str(error)
        finally:
            stream.close()

    def start(self, expected_models=()):
        if self.commands.server is not None:
            return
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 11435))
            except OSError as error:
                raise BenchmarkError("Port 11435 is occupied; refusing to reuse another server") from error
        help_text = self.cli("serve", "--help", timeout=30).stdout
        for name in ("OLLAMA_HOST", "OLLAMA_MODELS", "OLLAMA_NO_CLOUD", "OLLAMA_NUM_PARALLEL", "OLLAMA_MAX_LOADED_MODELS", "OLLAMA_CONTEXT_LENGTH", "OLLAMA_KV_CACHE_TYPE"):
            if name not in help_text:
                raise BenchmarkError(f"Installed Ollama does not advertise required environment setting {name}")
        for command, flags in (("run", ("--verbose",)), ("show", ("--parameters", "--modelfile"))):
            text = self.cli(command, "--help", timeout=30).stdout
            if any(flag not in text for flag in flags):
                raise BenchmarkError(f"Unsupported Ollama {command} CLI options")
        self.log_error = None
        self.commands.server = OwnedProcess([self.binary, "serve"], self.env, self.workspace, stderr=subprocess.STDOUT)
        server = self.commands.server
        self.log_thread = threading.Thread(target=self._capture_server_log, args=(server.child.stdout,), daemon=True)
        self.log_thread.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            self.check_server()
            if self.commands.guard:
                self.commands.guard.check()
            try:
                process = psutil.Process(server.child.pid)
                connections = process.net_connections(kind="tcp")
                if any(connection.status == psutil.CONN_LISTEN and connection.laddr.port == 11435 for connection in connections):
                    actual = process.environ()
                    for name, value in self.env.items():
                        if name.startswith("OLLAMA_") and actual.get(name) != value:
                            raise SafetyError(f"Server environment mismatch: {name}")
                    self.version = self.cli("--version", timeout=10).stdout.strip()
                    self.verify_store(expected_models)
                    return
            except psutil.Error as error:
                raise SafetyError(f"Cannot verify server ownership/environment: {error}") from error
            time.sleep(0.1)
        raise SafetyError("Owned Ollama server did not become ready")

    def verify_store(self, expected_models=()):
        listing = self.cli("list", timeout=10).stdout
        listed = {line.split()[0] for line in listing.splitlines()[1:] if line.strip()}
        if not listed.issubset(set(expected_models)):
            raise SafetyError("Owned model store contains unexpected models")

    def check_server(self):
        if self.log_error:
            raise SafetyError(self.log_error)
        if self.commands.server is not None and self.commands.server.child.poll() is not None:
            raise SafetyError("Owned Ollama server exited unexpectedly; inspect ollama.log")

    def stop_server(self):
        self.commands.stop_all()
        if self.log_thread is not None:
            self.log_thread.join(timeout=self.policy["execution"]["termination_grace_seconds"])
            if self.log_thread.is_alive():
                raise CleanupError("Server log reader did not stop")
            self.log_thread = None

    def pull(self, model, manifest):
        self.cli("pull", model["ollama_tag"], timeout=self.policy["execution"]["download_timeout_seconds"])
        self.verify_download(model, manifest)

    def pull_many(self, items):
        results = self.commands.pull_many([[self.binary, "pull", model["ollama_tag"]] for model, _ in items], self.env,
                                          self.policy["execution"]["download_timeout_seconds"])
        errors = []
        for (model, manifest), result in zip(items, results):
            try:
                if result.returncode:
                    raise BenchmarkError(f"Download exited {result.returncode}: {ANSI.sub('', result.stderr).strip()[-1500:]}")
                self.verify_download(model, manifest)
                errors.append(None)
            except (BenchmarkError, OSError) as error:
                errors.append(str(error))
        return errors

    def verify_download(self, model, manifest):
        self.verify_downloaded_manifest(model, manifest)
        for descriptor in [manifest.document["config"], *manifest.document["layers"]]:
            blob = self.store / "blobs" / descriptor["digest"].replace(":", "-")
            is_config = descriptor is manifest.document["config"]
            expected_size = manifest.config_size_bytes if is_config and manifest.config_size_bytes is not None else descriptor["size"]
            if not blob.is_file() or blob.stat().st_size != expected_size:
                raise BenchmarkError("Downloaded blob size differs from the admitted manifest")
            if is_config and "sha256:" + hashlib.sha256(blob.read_bytes()).hexdigest() != descriptor["digest"]:
                raise BenchmarkError("Downloaded config digest differs from the admitted manifest")
            if descriptor.get("mediaType") == "application/vnd.ollama.image.model":
                with blob.open("rb") as stream:
                    if stream.read(4) != b"GGUF":
                        raise BenchmarkError("Downloaded model layer is not GGUF")

    def verify_downloaded_manifest(self, model, manifest):
        family, revision = model["ollama_tag"].split(":")
        candidates = [
            self.store / "manifests-v2" / "ollama.com" / "library" / family / revision,
            self.store / "manifests" / "registry.ollama.ai" / "library" / family / revision,
            self.store / "manifests" / "ollama.com" / "library" / family / revision,
        ]
        local = next((path for path in candidates if path.exists() or path.is_symlink()), None)
        if local is None:
            raise BenchmarkError("Downloaded manifest not found in supported Ollama stores (manifests-v2 or manifests)")
        try:
            resolved = local.resolve(strict=True)
            if not resolved.is_relative_to(self.store.resolve()):
                raise BenchmarkError("Downloaded manifest resolves outside the owned model store")
            if local.is_symlink() and resolved != (self.store / "blobs" / f"sha256-{manifest.digest}").resolve():
                raise BenchmarkError("Downloaded manifest link differs from the admitted registry manifest digest")
            maximum = self.policy["disk"]["maximum_manifest_bytes"]
            with resolved.open("rb") as stream:
                raw = stream.read(maximum + 1)
            if len(raw) > maximum:
                raise BenchmarkError("Downloaded manifest exceeds its metadata byte limit")
        except (OSError, RuntimeError) as error:
            raise BenchmarkError(f"Cannot read downloaded manifest: {error}") from error
        if hashlib.sha256(raw).hexdigest() != manifest.digest:
            raise BenchmarkError("Downloaded manifest digest differs from the admitted registry manifest")

    def create_alias(self, model, probe=False):
        alias = f"local-bench-{model['id']}{'-probe' if probe else ''}"
        path = self.workspace / "Modelfile"
        path.write_text(modelfile(model["ollama_tag"], 1 if probe else 256))
        self.cli("create", alias, "-f", str(path.resolve()), timeout=self.policy["execution"]["load_timeout_seconds"])
        text = self.cli("show", alias, "--parameters").stdout
        for name, expected in self.catalog["benchmark"]["options"].items():
            match = re.search(rf"(?m)^\s*{name}\s+([-+\d.eE]+)\s*$", text)
            wanted = 1 if probe and name == "num_predict" else expected
            if not match or float(match[1]) != wanted:
                raise BenchmarkError(f"Ollama did not preserve requested parameter {name}")
        return alias

    def inspect(self, alias, expected):
        output = self.cli("show", alias).stdout
        match = re.search(r"(?im)^\s*quantization\s+(\S+)", output)
        if not match:
            raise BenchmarkError("Actual quantization unavailable from ollama show")
        actual = match[1]
        if expected is not None and actual.casefold() != expected.casefold():
            raise BenchmarkError(f"Quantization mismatch: expected {expected}, found {actual}")
        return actual

    def request(self, alias, prompt, first_load=False):
        self.check_server()
        result = self.cli("run", "--verbose", alias, prompt,
                          timeout=self.policy["execution"]["load_timeout_seconds" if first_load else "request_timeout_seconds"])
        metrics = parse_metrics(result.stderr, result.seconds)
        if metrics["prompt_tokens"] is None:
            raise BenchmarkError("CLI did not expose the rendered prompt token count")
        if metrics["prompt_tokens"] > self.catalog["benchmark"]["maximum_rendered_prompt_tokens"]:
            raise SafetyError("Rendered prompt exceeds the catalog token limit")
        if metrics["generated_tokens"] is not None and metrics["generated_tokens"] > self.catalog["benchmark"]["options"]["num_predict"]:
            raise SafetyError("Output token limit was not enforced")
        self.verify_loaded(alias)
        return metrics

    def verify_loaded(self, alias):
        output = ANSI.sub("", self.cli("ps").stdout)
        lines = [line for line in output.splitlines()[1:] if line.strip()]
        if len(lines) != 1 or lines[0].split()[0].removesuffix(":latest") != alias:
            raise SafetyError("Expected exactly one owned model loaded")
        match = re.search(r"\b100%\s+GPU\s+(\d+)\b", lines[0])
        if not match or int(match[1]) != self.catalog["benchmark"]["options"]["num_ctx"]:
            raise SafetyError("Actual backend/context mismatch; CPU or mixed offload is not permitted")

    def unload(self, alias):
        self.cli("stop", alias, timeout=self.policy["execution"]["unload_timeout_seconds"])
        listing = self.cli("ps").stdout
        if any(line.strip() for line in listing.splitlines()[1:]):
            raise CleanupError("Model remained loaded after ollama stop")

    def clear_model(self, aliases, source, successful, preserve_store=False):
        self.commands.guard = None
        if successful and self.commands.server is not None:
            try:
                for alias in reversed(aliases):
                    self.cli("stop", alias, timeout=self.policy["execution"]["unload_timeout_seconds"])
                    self.cli("rm", alias)
                listing = self.cli("ps").stdout
                if any(line.strip() for line in listing.splitlines()[1:]):
                    raise CleanupError("Owned model did not unload")
                self.cli("rm", source)
            except BenchmarkError as error:
                self.stop_server()
                raise CleanupError(f"CLI model cleanup failed: {error}") from error
        self.stop_server()
        for path in ((self.temporary, self.cache) if preserve_store else (self.store, self.temporary, self.cache)):
            if path.is_symlink() or path.parent != self.workspace:
                raise CleanupError("Refusing cleanup outside the owned workspace")
            shutil.rmtree(path)
            path.mkdir()
