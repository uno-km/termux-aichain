"""
==============================================================================
termux-aichain Core Engine: Local Server Fine-Tuning & Process Manager
==============================================================================
Provides fine-grained hardware and performance tuning parameters for
llama-server (llama.cpp) and BitNet.cpp across 0.5B to 14B model spectrum.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import time
import shutil
import collections
import threading
import subprocess
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class LocalServerConfig:
    """Comprehensive hardware & engine tuning configuration for local LLM servers."""
    model_path: str
    host: str = "127.0.0.1"
    port: int = 8080
    threads: int = field(default_factory=lambda: max(1, (os.cpu_count() or 4) - 1))
    n_ctx: int = 2048
    n_batch: int = 512
    n_ubatch: int = 256
    n_gpu_layers: int = 0
    flash_attn: bool = False
    cache_type_k: str = "f16"  # "f16", "q8_0", "q4_0"
    cache_type_v: str = "f16"  # "f16", "q8_0", "q4_0"
    mmap: bool = True
    mlock: bool = False
    cont_batching: bool = True
    rope_freq_base: Optional[float] = None
    rope_freq_scale: Optional[float] = None
    extra_args: List[str] = field(default_factory=list)

    def build_command(self, binary_name: str = "llama-server") -> List[str]:
        """Convenience method to generate full CLI arguments array."""
        return LocalServerManager(self, binary_name).build_cli_args()

class BoundedRingLog:
    """Thread-safe bounded ring log strictly enforcing max lines and max bytes (64KB default)."""
    def __init__(self, maxlen: int = 200, max_bytes: int = 65536):
        if maxlen < 1:
            raise ValueError("maxlen must be at least 1")
        if max_bytes < 1:
            raise ValueError("max_bytes must be at least 1")
        self.maxlen = maxlen
        self.max_bytes = max_bytes
        self.lines: collections.deque[str] = collections.deque()
        self._current_bytes = 0
        self._lock = threading.Lock()

    def append(self, line: str) -> None:
        clean_line = line.rstrip("\r\n")
        encoded = clean_line.encode("utf-8", errors="replace")
        if len(encoded) > self.max_bytes:
            encoded = encoded[-self.max_bytes:]
            clean_line = encoded.decode("utf-8", errors="ignore")
            encoded = clean_line.encode("utf-8", errors="replace")

        line_bytes = len(encoded)
        with self._lock:
            self.lines.append(clean_line)
            self._current_bytes += line_bytes
            while len(self.lines) > self.maxlen or self._current_bytes > self.max_bytes:
                if not self.lines:
                    break
                popped = self.lines.popleft()
                self._current_bytes -= len(popped.encode("utf-8", errors="replace"))
            self._current_bytes = max(0, self._current_bytes)

    def get_recent_lines(self, count: int = 20) -> List[str]:
        with self._lock:
            all_lines = list(self.lines)
            return all_lines[-count:] if len(all_lines) >= count else all_lines

    def get_recent_redacted_text(self, count: int = 20) -> str:
        lines = self.get_recent_lines(count)
        # Redact potential authorization tokens or private keys
        redacted = []
        for l in lines:
            if "bearer" in l.lower() or "key=" in l.lower():
                redacted.append("[REDACTED LOG LINE CONTAINING SENSITIVE DATA]")
            else:
                redacted.append(l)
        return "\n".join(redacted)

class LocalServerManager:
    """Manages lifecycle, healthcheck, and CLI argument generation for local LLM engines."""

    def __init__(self, config: LocalServerConfig, binary_name: str = "llama-server"):
        self.config = config
        self.binary_name = binary_name
        self.process: Optional[subprocess.Popen] = None
        self.ring_log = BoundedRingLog(maxlen=200)
        self._log_thread: Optional[threading.Thread] = None

    def build_cli_args(self) -> List[str]:
        """Constructs the complete CLI arguments based on fine-tuned config."""
        args = [
            self.binary_name,
            "-m", self.config.model_path,
            "--host", self.config.host,
            "--port", str(self.config.port),
            "-t", str(self.config.threads),
            "-c", str(self.config.n_ctx),
            "-b", str(self.config.n_batch),
            "--ubatch", str(self.config.n_ubatch),
        ]
        if self.config.n_gpu_layers > 0:
            args.extend(["-ngl", str(self.config.n_gpu_layers)])
        if self.config.flash_attn:
            args.append("-fa")
        if self.config.cache_type_k != "f16":
            args.extend(["-ctk", self.config.cache_type_k])
        if self.config.cache_type_v != "f16":
            args.extend(["-ctv", self.config.cache_type_v])
        if not self.config.mmap:
            args.append("--no-mmap")
        if self.config.mlock:
            args.append("--mlock")
        if self.config.cont_batching:
            args.append("--cont-batching")
        if self.config.rope_freq_base is not None:
            args.extend(["--rope-freq-base", str(self.config.rope_freq_base)])
        if self.config.rope_freq_scale is not None:
            args.extend(["--rope-freq-scale", str(self.config.rope_freq_scale)])
        
        args.extend(self.config.extra_args)
        return args

    def _drain_stderr(self, proc: subprocess.Popen) -> None:
        """Asynchronously drains stderr to prevent pipe buffer deadlock."""
        try:
            if proc.stderr:
                for line in iter(proc.stderr.readline, b""):
                    if not line:
                        break
                    self.ring_log.append(line.decode("utf-8", errors="replace"))
        except Exception:
            pass

    def start(self, wait_ready: bool = True, timeout: float = 30.0) -> bool:
        """Starts the server process in background and waits for health."""
        if not shutil.which(self.binary_name):
            raise FileNotFoundError(f"Local server binary '{self.binary_name}' not found in PATH.")

        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"Model file not found at: {self.config.model_path}")

        cmd = self.build_cli_args()
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        self._log_thread = threading.Thread(target=self._drain_stderr, args=(self.process,), daemon=True)
        self._log_thread.start()

        if wait_ready:
            return self.wait_until_ready(timeout=timeout)
        return True

    def is_healthy(self) -> bool:
        """Checks if the local server HTTP health endpoint responds 200 OK."""
        url = f"http://{self.config.host}:{self.config.port}/health"
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def wait_until_ready(self, timeout: float = 30.0) -> bool:
        """Polls health until the model is fully loaded into memory."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.process and self.process.poll() is not None:
                recent_logs = self.ring_log.get_recent_redacted_text(20)
                raise RuntimeError(
                    f"Server process terminated prematurely with exit code {self.process.returncode}.\n"
                    f"Recent Server Diagnostics:\n{recent_logs}"
                )
            if self.is_healthy():
                return True
            time.sleep(0.5)
        recent_logs = self.ring_log.get_recent_redacted_text(20)
        raise TimeoutError(
            f"Server at port {self.config.port} did not become ready within {timeout}s.\n"
            f"Recent Server Diagnostics:\n{recent_logs}"
        )

    def stop(self) -> None:
        """Gracefully terminates server and frees RAM/VRAM."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None

    def __enter__(self) -> LocalServerManager:
        self.start(wait_ready=True)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    @classmethod
    def launch_and_connect(
        cls,
        model_path: str,
        host: str = "127.0.0.1",
        port: int = 8080,
        threads: Optional[int] = None,
        n_ctx: int = 2048,
        binary_name: str = "llama-server",
        temperature: float = 0.1,
        max_tokens: int = 256,
        timeout: float = 30.0
    ):
        """One-touch launcher that spins up a local server and returns a connected OpenAICompatibleChat client."""
        from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat
        actual_threads = threads or max(1, (os.cpu_count() or 4) - 1)
        config = LocalServerConfig(
            model_path=model_path,
            host=host,
            port=port,
            threads=actual_threads,
            n_ctx=n_ctx
        )
        manager = cls(config, binary_name=binary_name)
        manager.start(wait_ready=True, timeout=timeout)
        client = OpenAICompatibleChat(
            base_url=f"http://{host}:{port}/v1",
            model=os.path.basename(model_path),
            temperature=temperature,
            max_tokens=max_tokens
        )
        # Attach manager to client for automatic lifecycle management
        client._local_server_manager = manager
        return client

class LlamaCppServer(LocalServerManager):
    """Specialized manager for llama.cpp server instances."""
    def __init__(self, config: LocalServerConfig):
        super().__init__(config, binary_name="llama-server")

class BitNetServer(LocalServerManager):
    """Specialized manager for BitNet.cpp 1-bit server instances."""
    def __init__(self, config: LocalServerConfig):
        super().__init__(config, binary_name="bitnet-server" if shutil.which("bitnet-server") else "llama-server")