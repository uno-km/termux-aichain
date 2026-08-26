"""
==============================================================================
termux-aichain LocalAgent: 4-Mode Enterprise Agent Runtime
==============================================================================
Implements connect, managed, embedded, and remote modes with atomic OS file locks,
background idle eviction monitors, lease management, fail-closed tool policies,
URL structure validation, and protocol identity handshakes.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import sys
import time
import json
import shutil
import hashlib
import inspect
import tempfile
import threading
import subprocess
import urllib.request
import urllib.parse
import ipaddress
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

from termux_aichain.core.schema import Message, HumanMessage, AIMessage, ToolMessage
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat
from termux_aichain.graph.agent import Tool, tool, create_react_agent
from termux_aichain.graph.state import CompiledGraph
from termux_aichain.output.normalizer import validate_tool_arguments, OutputParserPolicy
from termux_aichain.core.agent_types import (
    AgentState,
    ConnectConfig,
    ManagedConfig,
    EmbeddedConfig,
    RemoteConfig,
    ToolPolicy,
    ToolRule,
    LocalAgentError,
    ServerConnectionRefusedError,
    ServerProtocolMismatchError,
    ModelIdentityMismatchError,
    ManagedSpawnNotSupportedError,
    ServerStartupTimeoutError,
    DuplicateServerOwnershipError,
    RemoteFallbackNotAuthorizedError,
    ToolApprovalRequiredError,
    ToolArgumentValidationError,
    ToolRateLimitExceededError,
    ToolPolicyDeniedError,
    NativeBackendUnavailableError,
)

class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """P1-1: Strict security handler rejecting HTTP redirects on health endpoints."""
    def http_error_301(self, req, fp, code, msg, headers):
        raise ServerProtocolMismatchError(f"Health endpoint HTTP redirect ({code}) is forbidden.")
    http_error_302 = http_error_301
    http_error_303 = http_error_301
    http_error_307 = http_error_301
    http_error_308 = http_error_301

def validate_loopback_endpoint(endpoint: str) -> None:
    """P0-5: Strict structural URL parse preventing prefix bypass (e.g. localhost.evil.example)."""
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ServerConnectionRefusedError(f"Unsupported endpoint scheme '{parsed.scheme}'. Only http/https supported.")

    hostname = parsed.hostname
    if not hostname:
        raise ServerConnectionRefusedError("Endpoint hostname is missing.")

    # Rejection of userinfo trick (e.g. http://localhost@evil.example)
    if parsed.username or parsed.password:
        raise ServerConnectionRefusedError("Userinfo credentials inside loopback endpoint URL are forbidden.")

    if hostname.lower() == "localhost":
        return

    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError as ex:
        raise ServerConnectionRefusedError(f"Endpoint hostname '{hostname}' is not a valid loopback address.") from ex

    if not addr.is_loopback:
        raise ServerConnectionRefusedError(f"Endpoint address '{addr}' violates 'loopback_only' transport policy.")

class ServerIdentityVerifier:
    """P0-6 & P0-7: Fail-closed identity verification shared between Connect and Managed modes."""

    @staticmethod
    def verify(
        endpoint_url: str,
        timeout_seconds: float = 10.0,
        max_health_bytes: int = 65536,
        expected_service: Optional[str] = None,
        expected_protocol_version: str = "1.0",
        expected_model_id: Optional[str] = None,
        expected_model_sha256: Optional[str] = None,
        require_model_identity: bool = False
    ) -> Dict[str, Any]:
        health_url = f"{endpoint_url.rstrip('/')}/health"
        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            req = urllib.request.Request(health_url, headers={"Accept": "application/json"})
            with opener.open(req, timeout=timeout_seconds) as resp:
                if resp.status != 200:
                    raise ServerConnectionRefusedError(f"Healthcheck returned non-200 HTTP status: {resp.status}.")
                raw_data = resp.read(max_health_bytes + 1)
                if len(raw_data) > max_health_bytes:
                    raise ServerProtocolMismatchError("Health response exceeds maximum allowed size.")
        except (ServerConnectionRefusedError, ServerProtocolMismatchError):
            raise
        except Exception as ex:
            raise ServerConnectionRefusedError(f"Cannot connect to server at {endpoint_url}: {str(ex)}")

        try:
            payload = json.loads(raw_data.decode("utf-8"))
        except Exception as ex:
            raise ServerProtocolMismatchError("Health response is not valid JSON (Fail-closed).") from ex

        if not isinstance(payload, dict) or not payload:
            raise ServerProtocolMismatchError("Health response payload must be a non-empty JSON object.")

        service_id = payload.get("service")
        if not service_id or service_id not in {"llama-server", "bitnet-server", "termux-aichain"}:
            raise ServerProtocolMismatchError(f"Incompatible or missing service identity '{service_id}'.")

        if expected_service and service_id != expected_service:
            raise ServerProtocolMismatchError(f"Service mismatch: expected '{expected_service}', got '{service_id}'.")

        proto_ver = payload.get("protocolVersion")
        if proto_ver != expected_protocol_version:
            raise ServerProtocolMismatchError(f"Protocol version mismatch: expected '{expected_protocol_version}', got '{proto_ver}'.")

        model_info = payload.get("model", {})
        actual_model_id = model_info.get("id")
        actual_sha256 = model_info.get("sha256")

        if expected_model_id and actual_model_id != expected_model_id:
            raise ModelIdentityMismatchError(f"Model ID mismatch: expected '{expected_model_id}', got '{actual_model_id}'.")

        if expected_model_sha256 and actual_sha256 != expected_model_sha256:
            raise ModelIdentityMismatchError(f"Model checksum mismatch: expected '{expected_model_sha256}', got '{actual_sha256}'.")

        if require_model_identity and not actual_model_id and not actual_sha256:
            raise ModelIdentityMismatchError("Server did not report model identity while require_model_identity is True.")

        return payload

class AgentLease:
    """P1-3: Context manager managing client lease lifecycle with inactive state checks."""
    def __init__(self, agent: LocalAgent):
        self.agent = agent
        self._acquired = False

    def __enter__(self) -> AgentLease:
        with self.agent._lock:
            if self.agent.state in {AgentState.STOPPING, AgentState.STOPPED, AgentState.FAILED}:
                raise LocalAgentError(f"Cannot acquire lease for inactive agent in state '{self.agent.state.value}'.")
            self.agent.connected_leases += 1
            self.agent.last_activity_monotonic = time.monotonic()
            self._acquired = True
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._acquired:
            with self.agent._lock:
                self.agent.connected_leases = max(0, self.agent.connected_leases - 1)
                self.agent.last_activity_monotonic = time.monotonic()
                self._acquired = False

class LocalAgent:
    """Enterprise 4-Mode Local Agent Runtime with fail-closed security and atomic lifecycle."""

    def __init__(
        self,
        mode: str,
        chat_model: BaseChatModel,
        tools: Sequence[Union[Tool, Callable[..., Any]]],
        tool_policy: Optional[ToolPolicy] = None,
        system_prompt: Optional[str] = None,
        managed_process: Optional[subprocess.Popen] = None,
        lock_file_path: Optional[Path] = None,
        lock_handle: Optional[Any] = None,
        owns_managed_process: bool = False,
        owns_identity_lock: bool = False,
        idle_timeout_seconds: float = 300.0,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ):
        self.mode = mode
        self.chat_model = chat_model
        self.tools = list(tools)
        self.tool_policy = tool_policy or ToolPolicy(default="deny")
        self.system_prompt = system_prompt
        self.managed_process = managed_process
        self.lock_file_path = lock_file_path
        self.lock_handle = lock_handle
        self.owns_managed_process = owns_managed_process
        self.owns_identity_lock = owns_identity_lock
        self.idle_timeout_seconds = idle_timeout_seconds
        self.approval_callback = approval_callback

        self.state = AgentState.READY
        self._lock = threading.Lock()
        self.active_requests = 0
        self.queued_requests = 0
        self.connected_leases = 0
        self.last_activity_monotonic = time.monotonic()
        self._tool_invocation_history: Dict[str, List[float]] = {}
        self._stop_monitor = threading.Event()

        guarded_tools = [self._wrap_tool_with_policy(t) for t in self.tools]
        self._graph: CompiledGraph = create_react_agent(
            model=self.chat_model,
            tools=guarded_tools,
            system_prompt=self.system_prompt
        )

        self._monitor_thread: Optional[threading.Thread] = None
        if self.mode == "managed" and self.owns_managed_process:
            self._monitor_thread = threading.Thread(target=self._idle_supervisor_loop, daemon=True)
            self._monitor_thread.start()

    def acquire_lease(self) -> AgentLease:
        """Acquires a client lease to prevent idle eviction during active workflow."""
        return AgentLease(self)

    def _wrap_tool_with_policy(self, t: Union[Tool, Callable[..., Any]]) -> Tool:
        """Wraps a tool with JSON Schema validation, strict binding, and policy checks."""
        raw_tool = t if isinstance(t, Tool) else Tool(name=getattr(t, "__name__", "tool"), description=getattr(t, "__doc__", "") or "", func=t)

        def guarded_func(*args: Any, **kwargs: Any) -> Any:
            tool_name = raw_tool.name
            now = time.monotonic()

            # P0-4: Strict Signature Binding
            sig = inspect.signature(raw_tool.func)
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                all_args = dict(bound.arguments)
            except TypeError as ex:
                raise ToolArgumentValidationError(f"Invalid arguments for tool '{tool_name}': {str(ex)}")

            # P0-3: Strict JSON Schema Validation
            if raw_tool.parameters:
                validate_tool_arguments(raw_tool.parameters, all_args)

            requires_approval = False

            with self._lock:
                if self.tool_policy.default == "deny" and tool_name not in self.tool_policy.allowed_tools:
                    raise ToolPolicyDeniedError(f"Tool '{tool_name}' is denied by security policy (default=deny).")

                rule_raw = self.tool_policy.allowed_tools.get(tool_name, ToolRule())
                rule = rule_raw if isinstance(rule_raw, ToolRule) else ToolRule(**rule_raw)

                history = self._tool_invocation_history.setdefault(tool_name, [])
                history = [ts for ts in history if now - ts < 60.0]
                self._tool_invocation_history[tool_name] = history

                if len(history) >= rule.max_calls_per_minute:
                    raise ToolRateLimitExceededError(f"Rate limit exceeded for tool '{tool_name}': max {rule.max_calls_per_minute}/min.")

                for param_name, val in all_args.items():
                    if param_name in rule.allowed_ranges:
                        min_val, max_val = rule.allowed_ranges[param_name]
                        if isinstance(val, bool):
                            raise ToolArgumentValidationError(f"Argument '{param_name}' must be an integer, bool is rejected.")
                        if not isinstance(val, (int, float)) or not (min_val <= val <= max_val):
                            raise ToolArgumentValidationError(
                                f"Argument '{param_name}' value {val} violates allowed range [{min_val}, {max_val}]."
                            )

                if rule.approval in ("explicit_prompt", "token_verified"):
                    requires_approval = True

            if requires_approval:
                if not self.approval_callback:
                    raise ToolApprovalRequiredError(f"Tool '{tool_name}' requires approval but no callback was registered.")
                approved = self.approval_callback(tool_name, all_args)
                if not approved:
                    raise ToolApprovalRequiredError(f"Invocation of tool '{tool_name}' was rejected by user approval.")

            with self._lock:
                self._tool_invocation_history[tool_name].append(now)

            return raw_tool(*bound.args, **bound.kwargs)

        return Tool(name=raw_tool.name, description=raw_tool.description, func=guarded_func, parameters=raw_tool.parameters, aliases=raw_tool.aliases)

    def invoke(self, input_data: Dict[str, Any], max_iterations: int = 10) -> Dict[str, Any]:
        """Executes the agent loop while tracking monotonic activity and validating state."""
        with self._lock:
            # P0-9: Reject requests if agent is shutting down or stopped
            if self.state in {AgentState.STOPPING, AgentState.STOPPED, AgentState.FAILED}:
                raise LocalAgentError(f"Agent cannot accept requests in state '{self.state.value}'.")
            self.active_requests += 1
            self.state = AgentState.BUSY
            self.last_activity_monotonic = time.monotonic()

        try:
            res = self._graph.invoke(input_data, max_iterations=max_iterations)
            return res
        finally:
            with self._lock:
                self.active_requests = max(0, self.active_requests - 1)
                self.last_activity_monotonic = time.monotonic()
                if self.state not in {AgentState.STOPPING, AgentState.STOPPED}:
                    self.state = AgentState.READY if self.active_requests == 0 else AgentState.BUSY

    def _idle_supervisor_loop(self) -> None:
        """Background supervisor polling idle eviction using monotonic intervals."""
        while not self._stop_monitor.is_set():
            time.sleep(1.0)
            should_close = False
            with self._lock:
                now = time.monotonic()
                if (
                    self.state == AgentState.READY
                    and self.active_requests == 0
                    and self.queued_requests == 0
                    and self.connected_leases == 0
                    and (now - self.last_activity_monotonic) >= self.idle_timeout_seconds
                ):
                    self.state = AgentState.STOPPING
                    should_close = True

            if should_close:
                self.close()
                break

    def check_idle_and_evict(self) -> bool:
        """Evaluates idle eviction policy using monotonic clock."""
        should_close = False
        with self._lock:
            now = time.monotonic()
            is_idle = (
                self.active_requests == 0
                and self.queued_requests == 0
                and self.connected_leases == 0
                and (now - self.last_activity_monotonic) >= self.idle_timeout_seconds
            )
            if is_idle and self.mode == "managed" and self.owns_managed_process:
                self.state = AgentState.STOPPING
                should_close = True

        if should_close:
            self.close()
            return True
        return False

    def status(self) -> Dict[str, Any]:
        """Returns structured JSON status payload matching common state machine."""
        with self._lock:
            return {
                "mode": self.mode,
                "state": self.state.value,
                "active_requests": self.active_requests,
                "connected_leases": self.connected_leases,
                "idle_duration_seconds": round(time.monotonic() - self.last_activity_monotonic, 2),
                "pid": self.managed_process.pid if self.managed_process else os.getpid(),
                "tools_registered": [t.name for t in self.tools],
                "capabilities": ["chat", "streaming", "tool_calls"]
            }

    def close(self) -> None:
        """P0-5 & P0-8: Idempotent graceful termination of owned processes and locks."""
        self._stop_monitor.set()
        with self._lock:
            if self.state == AgentState.STOPPED:
                return
            self.state = AgentState.STOPPING

        if self.owns_managed_process and self.managed_process and self.managed_process.poll() is None:
            self.managed_process.terminate()
            try:
                self.managed_process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self.managed_process.kill()
            self.managed_process = None

        if self.owns_identity_lock:
            if self.lock_handle:
                try:
                    if fcntl:
                        fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
                    elif msvcrt:
                        self.lock_handle.seek(0)
                        msvcrt.locking(self.lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    self.lock_handle.close()
                except Exception:
                    pass
                self.lock_handle = None

            if self.lock_file_path and self.lock_file_path.exists():
                try:
                    self.lock_file_path.unlink()
                except Exception:
                    pass

        with self._lock:
            self.state = AgentState.STOPPED

    @classmethod
    def create(
        cls,
        mode: str = "connect",
        model_path: Optional[str] = None,
        endpoint: Optional[str] = None,
        connect: Optional[ConnectConfig] = None,
        managed: Optional[ManagedConfig] = None,
        embedded: Optional[EmbeddedConfig] = None,
        remote: Optional[RemoteConfig] = None,
        tools: Optional[Sequence[Union[Tool, Callable[..., Any]]]] = None,
        tool_policy: Optional[ToolPolicy] = None,
        system_prompt: Optional[str] = None,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ) -> LocalAgent:
        """Factory creating LocalAgent in one of 4 explicit modes with atomic OS locks and safety guardrails."""
        tools_list = list(tools or [])

        # ======================================================================
        # Mode 1: CONNECT
        # ======================================================================
        if mode == "connect":
            cfg = connect or ConnectConfig()
            target_endpoint = endpoint or "http://127.0.0.1:8080"

            if cfg.transport_policy == "loopback_only":
                validate_loopback_endpoint(target_endpoint)

            ServerIdentityVerifier.verify(
                endpoint_url=target_endpoint,
                timeout_seconds=cfg.timeout_seconds,
                max_health_bytes=cfg.max_health_bytes,
                expected_protocol_version=cfg.protocol_version,
                expected_model_id=cfg.expected_model_id,
                expected_model_sha256=cfg.expected_model_sha256
            )

            chat = OpenAICompatibleChat(base_url=f"{target_endpoint.rstrip('/')}/v1", model=cfg.expected_model_id or "default")
            return cls(
                mode="connect",
                chat_model=chat,
                tools=tools_list,
                tool_policy=tool_policy,
                system_prompt=system_prompt,
                owns_managed_process=False,
                owns_identity_lock=False,
                approval_callback=approval_callback
            )

        # ======================================================================
        # Mode 2: MANAGED
        # ======================================================================
        elif mode == "managed":
            if not model_path or not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found for managed mode: {model_path}")

            m_cfg = managed or ManagedConfig()
            if not shutil.which(m_cfg.binary_name):
                raise ManagedSpawnNotSupportedError(f"Server binary '{m_cfg.binary_name}' not found in system PATH.")

            lock_dir = Path(tempfile.gettempdir()) / "termux-aichain"
            lock_dir.mkdir(parents=True, exist_ok=True)
            identity_key = f"{model_path}|127.0.0.1:8080|{m_cfg.binary_name}|{m_cfg.n_ctx}"
            lock_id = hashlib.sha256(identity_key.encode("utf-8")).hexdigest()[:16]
            lock_file = lock_dir / f"server-{lock_id}.lock"

            port = 8080
            endpoint_url = f"http://127.0.0.1:{port}"

            def inspect_existing_server() -> Tuple[str, Optional[Dict[str, Any]]]:
                """P0-4: Distinguish between ABSENT, CONFLICT, and VERIFIED server states."""
                try:
                    payload = ServerIdentityVerifier.verify(
                        endpoint_url=endpoint_url,
                        timeout_seconds=1.0,
                        expected_service=m_cfg.binary_name.replace(".exe", ""),
                        expected_model_id=os.path.basename(model_path)
                    )
                    return "VERIFIED", payload
                except ServerConnectionRefusedError:
                    return "ABSENT", None
                except (ServerProtocolMismatchError, ModelIdentityMismatchError):
                    return "CONFLICT", None
                except Exception:
                    return "CONFLICT", None

            server_status, payload = inspect_existing_server()

            if server_status == "CONFLICT":
                raise DuplicateServerOwnershipError("Port is occupied by an incompatible or conflicting server identity.")

            if server_status == "VERIFIED":
                chat = OpenAICompatibleChat(base_url=f"{endpoint_url}/v1", model=os.path.basename(model_path))
                return cls(
                    mode="managed",
                    chat_model=chat,
                    tools=tools_list,
                    tool_policy=tool_policy,
                    system_prompt=system_prompt,
                    managed_process=None,
                    lock_file_path=None,
                    lock_handle=None,
                    owns_managed_process=False,
                    owns_identity_lock=False,
                    runtime_ownership="ATTACHED",
                    idle_timeout_seconds=m_cfg.idle_timeout_seconds,
                    approval_callback=approval_callback
                )

            lock_handle = lock_file.open("a+")
            owns_lock = False
            try:
                if fcntl:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    owns_lock = True
                elif msvcrt:
                    lock_handle.seek(0)
                    lock_handle.write("\0")
                    lock_handle.flush()
                    lock_handle.seek(0)
                    msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
                    owns_lock = True
                else:
                    owns_lock = True
            except (BlockingIOError, IOError, OSError):
                owns_lock = False

            if not owns_lock:
                lock_handle.close()
                lock_handle = None
                t0 = time.time()
                while time.time() - t0 < m_cfg.startup_timeout_seconds:
                    status, _ = inspect_existing_server()
                    if status == "VERIFIED":
                        chat = OpenAICompatibleChat(base_url=f"{endpoint_url}/v1", model=os.path.basename(model_path))
                        return cls(
                            mode="managed",
                            chat_model=chat,
                            tools=tools_list,
                            tool_policy=tool_policy,
                            system_prompt=system_prompt,
                            managed_process=None,
                            lock_file_path=None,
                            lock_handle=None,
                            owns_managed_process=False,
                            owns_identity_lock=False,
                            runtime_ownership="ATTACHED",
                            idle_timeout_seconds=m_cfg.idle_timeout_seconds,
                            approval_callback=approval_callback
                        )
                    elif status == "CONFLICT":
                        raise DuplicateServerOwnershipError("Other lock owner started an incompatible server identity.")
                    time.sleep(0.5)

                raise DuplicateServerOwnershipError("Existing lock owner failed to bring server online within deadline.")

            proc: Optional[subprocess.Popen] = None
            try:
                actual_threads = m_cfg.threads or max(1, (os.cpu_count() or 4) - 1)
                cmd = [
                    m_cfg.binary_name,
                    "-m", model_path,
                    "--host", "127.0.0.1",
                    "--port", str(port),
                    "-t", str(actual_threads),
                    "-c", str(m_cfg.n_ctx)
                ]
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                t0 = time.time()
                ready = False
                while time.time() - t0 < m_cfg.startup_timeout_seconds:
                    if proc.poll() is not None:
                        raise ServerStartupTimeoutError(f"Managed server exited prematurely with code {proc.returncode}.")
                    status, _ = inspect_existing_server()
                    if status == "VERIFIED":
                        ready = True
                        break
                    time.sleep(0.5)

                if not ready:
                    raise ServerStartupTimeoutError(f"Managed server failed to initialize within {m_cfg.startup_timeout_seconds}s.")

                lock_meta = {
                    "pid": proc.pid,
                    "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "endpoint": endpoint_url,
                    "modelPath": model_path,
                    "protocolVersion": "1.0"
                }
                lock_handle.seek(0)
                lock_handle.truncate()
                lock_handle.write(json.dumps(lock_meta, indent=2))
                lock_handle.flush()

                chat = OpenAICompatibleChat(base_url=f"{endpoint_url}/v1", model=os.path.basename(model_path))
                return cls(
                    mode="managed",
                    chat_model=chat,
                    tools=tools_list,
                    tool_policy=tool_policy,
                    system_prompt=system_prompt,
                    managed_process=proc,
                    lock_file_path=lock_file,
                    lock_handle=lock_handle,
                    owns_managed_process=True,
                    owns_identity_lock=True,
                    runtime_ownership="OWNED",
                    idle_timeout_seconds=m_cfg.idle_timeout_seconds,
                    approval_callback=approval_callback
                )

            except Exception:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except Exception:
                        proc.kill()

                if lock_handle:
                    try:
                        if fcntl:
                            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                        elif msvcrt:
                            lock_handle.seek(0)
                            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                        lock_handle.close()
                    except Exception:
                        pass

                if lock_file.exists():
                    try:
                        lock_file.unlink()
                    except Exception:
                        pass
                raise

        # ======================================================================
        # Mode 3: EMBEDDED
        # ======================================================================
        elif mode == "embedded":
            e_cfg = embedded or EmbeddedConfig()
            raise NativeBackendUnavailableError(
                f"Embedded native C/FFI backend '{e_cfg.backend}' is not compiled into the current package. "
                "Use mode='managed' or mode='connect' on Android Termux."
            )

        # ======================================================================
        # Mode 4: REMOTE (Option A: Safe RC Isolation)
        # ======================================================================
        elif mode == "remote":
            raise RemoteFallbackNotAuthorizedError("Remote mode is not available in this release candidate (v1.0.12-rc).")

        # ======================================================================
        # Mode 5: AUTO
        # ======================================================================
        elif mode == "auto":
            try:
                return cls.create(mode="connect", endpoint=endpoint, connect=connect, tools=tools_list, tool_policy=tool_policy, system_prompt=system_prompt, approval_callback=approval_callback)
            except ServerConnectionRefusedError:
                if model_path:
                    return cls.create(mode="managed", model_path=model_path, managed=managed, tools=tools_list, tool_policy=tool_policy, system_prompt=system_prompt, approval_callback=approval_callback)
                raise LocalAgentError("Auto mode could not find an active server and no model_path was provided for managed spawn.")

        else:
            raise ValueError(f"Unknown execution mode '{mode}'. Choose from 'connect', 'managed', 'embedded', 'remote', or 'auto'.")