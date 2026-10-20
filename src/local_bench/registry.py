import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import os
import sys
from pathlib import Path
from dataclasses import dataclass

from .config import BenchmarkError

MANIFEST_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
DIGEST = re.compile(r"sha256:[a-f0-9]{64}")


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        target = urllib.parse.urlparse(new_url)
        allowed = target.hostname and any(target.hostname == suffix or target.hostname.endswith("." + suffix) for suffix in ("ollama.ai", "ollama.com", "r2.cloudflarestorage.com"))
        if target.scheme != "https" or not allowed:
            raise BenchmarkError("Registry redirect to an unapproved host")
        redirected = super().redirect_request(request, response, code, message, headers, new_url)
        if urllib.parse.urlparse(request.full_url).hostname != target.hostname:
            redirected.remove_header("Authorization")
        return redirected


@dataclass
class Manifest:
    digest: str
    document: dict
    payload_bytes: int
    quantization: str | None


def validate_manifest(raw, model, policy, config):
    digest = hashlib.sha256(raw).hexdigest()
    prefix = model["provenance"]["observed_manifest_sha256_prefix"]
    if not digest.startswith(prefix):
        raise BenchmarkError(f"tag_digest_changed: expected {prefix}, got {digest}; review catalog")
    try:
        document = json.loads(raw)
        if not isinstance(document, dict) or not isinstance(config, dict):
            raise BenchmarkError("Manifest and model config must be JSON objects")
        if document.get("mediaType") != MANIFEST_TYPE or document.get("schemaVersion") != 2:
            raise BenchmarkError("Manifest indexes and non-v2 artifacts are unsupported")
        layers = document["layers"]
        if not isinstance(layers, list) or not layers or len(layers) > 256:
            raise BenchmarkError("Invalid manifest layers")
        descriptors = [document["config"], *layers]
        total = 0
        for descriptor in descriptors:
            size = descriptor["size"]
            if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= policy["disk"]["maximum_single_manifest_layer_bytes"]:
                raise BenchmarkError("Invalid or oversized manifest layer")
            if not DIGEST.fullmatch(descriptor["digest"]):
                raise BenchmarkError("Invalid layer digest")
            total += size
        if total > model["resources"]["download_bytes_upper_bound"]:
            raise BenchmarkError("Live manifest exceeds the catalog download bound")
        if config.get("model_format") != "gguf" or config.get("remote_host") or config.get("remote_model"):
            raise BenchmarkError("Artifact is not a local GGUF model")
        if not any(layer.get("mediaType") == "application/vnd.ollama.image.model" for layer in layers):
            raise BenchmarkError("No GGUF model layer")
        return Manifest(digest, document, total, config.get("file_type"))
    except (ValueError, TypeError, KeyError) as error:
        raise BenchmarkError(f"Malformed registry manifest: {error}") from error


class Registry:
    def __init__(self, policy, commands=None):
        self.policy = policy
        self.commands = commands
        self.token = None
        self.opener = urllib.request.build_opener(SafeRedirect())

    def fetch(self, url, maximum, guard=None):
        if self.commands is not None:
            timeout = self.policy["integrity"]["metadata_fetch_timeout_seconds"]
            worker = Path(__file__).with_name("metadata_worker.py")
            result = self.commands.run([sys.executable, str(worker), url, str(maximum), str(timeout)],
                                       os.environ.copy(), timeout)
            raw = result.stdout.encode("utf-8")
            if len(raw) > maximum:
                raise BenchmarkError("Registry metadata exceeded its byte limit")
            return raw
        if guard is not None:
            raise BenchmarkError("Guarded metadata requests require the subprocess runner")
        return self._fetch_blocking(url, maximum)

    def _fetch_blocking(self, url, maximum):
        headers = {"Accept": MANIFEST_TYPE, "User-Agent": "local-ai-benchmark/0.1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        timeout = min(10, self.policy["integrity"]["metadata_fetch_timeout_seconds"])
        try:
            with self.opener.open(request, timeout=timeout) as response:
                result = bytearray()
                while True:
                    chunk = response.read(min(65536, maximum + 1 - len(result)))
                    if not chunk:
                        return bytes(result)
                    result.extend(chunk)
                    if len(result) > maximum:
                        raise BenchmarkError("Registry metadata exceeded its byte limit")
        except urllib.error.HTTPError as error:
            if error.code == 401 and self.token is None:
                challenge = error.headers.get("WWW-Authenticate", "")
                parameters = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
                realm = parameters.get("realm", "")
                parsed = urllib.parse.urlparse(realm)
                if parsed.scheme != "https" or parsed.hostname not in {"ollama.com", "registry.ollama.ai"}:
                    raise BenchmarkError("Unapproved registry auth realm") from error
                query = urllib.parse.urlencode({key: parameters[key] for key in ("service", "scope") if key in parameters})
                auth_url = realm + ("&" if "?" in realm else "?") + query
                self.token = "auth-in-progress"
                data = json.loads(self._fetch_blocking(auth_url, 65536))
                self.token = data.get("token") or data.get("access_token")
                if not isinstance(self.token, str) or not self.token:
                    raise BenchmarkError("Registry did not issue a public pull token")
                return self._fetch_blocking(url, maximum)
            raise BenchmarkError(f"Registry HTTP error: {error.code}") from error
        except (OSError, ValueError) as error:
            raise BenchmarkError(f"Registry metadata fetch failed: {error}") from error

    def resolve(self, model, guard=None):
        raw = self.fetch(model["provenance"]["manifest_url"], self.policy["disk"]["maximum_manifest_bytes"], guard)
        digest = hashlib.sha256(raw).hexdigest()
        if not digest.startswith(model["provenance"]["observed_manifest_sha256_prefix"]):
            raise BenchmarkError(f"tag_digest_changed: {digest}; review catalog before downloading")
        try:
            descriptor = json.loads(raw)["config"]
            if not DIGEST.fullmatch(descriptor["digest"]) or not isinstance(descriptor["size"], int) or isinstance(descriptor["size"], bool) or not 0 < descriptor["size"] <= self.policy["disk"]["maximum_manifest_bytes"]:
                raise BenchmarkError("Invalid registry config descriptor")
            family = model["ollama_tag"].split(":")[0]
            config_url = f"https://registry.ollama.ai/v2/library/{family}/blobs/{descriptor['digest']}"
            config_raw = self.fetch(config_url, descriptor["size"], guard)
            if len(config_raw) != descriptor["size"] or "sha256:" + hashlib.sha256(config_raw).hexdigest() != descriptor["digest"]:
                raise BenchmarkError("Registry config size/digest mismatch")
            return validate_manifest(raw, model, self.policy, json.loads(config_raw))
        except (ValueError, TypeError, KeyError) as error:
            raise BenchmarkError(f"Malformed registry metadata: {error}") from error
