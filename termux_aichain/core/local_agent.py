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
import hmac
import inspect
import tempfile
import threading
import subprocess
import urllib.request
import urllib.parse
import ipaddress
from pathlib import Path
from dataclasses import dataclass
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

@dataclass(frozen=True)
class ServerIdentityProfile:
    """Capability and contract profile for diverse local server backends."""
    service: str
    require_protocol_version: bool = False
    expected_protocol_version: Optional[str] = None
    require_model_endpoint: bool = False

SERVER_PROFILES: Dict[str, ServerIdentityProfile] = {
    "termux-aichain": ServerIdentityProfile(
        service="termux-aichain",
        require_protocol_version=True,
        expected_protocol_version="1.0",
        require_model_endpoint=False
    ),
    "llama-server": ServerIdentityProfile(
        service="llama-server",
        require_protocol_version=False,
        expected_protocol_version=None,
        require_model_endpoint=True
    ),
    "bitnet-server": ServerIdentityProfile(
        service="bitnet-server",
        require_protocol_version=False,
        expected_protocol_version=None,
        require_model_endpoint=True
    ),
    "openai-compatible": ServerIdentityProfile(
        service="openai-compatible",
        require_protocol_version=False,
        expected_protocol_version=None,
        require_model_endpoint=False
    ),
}

class ServerIdentityVerifier:
    """P0-2 & P0-3: Fail-closed identity verification with exact service classification and capability profiles."""

    @staticmethod
    def verify(
        endpoint_url: str,
        timeout_seconds: float = 10.0,
        max_health_bytes: int = 65536,
        expected_service: Optional[str] = None,
        expected_protocol_version: Optional[str] = None,
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

        # P0-3: Process liveness vs explicit service classification
        status_field = payload.get("status")
        service_id = payload.get("service") or payload.get("engine")

        if not service_id:
            if status_field in {"ok", "loading model", "success"}:
                service_id = "openai-compatible"  # Generic capability baseline
            else:
                raise ServerProtocolMismatchError(f"Incompatible or missing service status (status='{status_field}').")

        allowed_services = set(SERVER_PROFILES.keys())
        if service_id not in allowed_services:
            raise ServerProtocolMismatchError(f"Incompatible service identity '{service_id}'. Allowed: {sorted(allowed_services)}")

        # Capability profile resolution
        profile = SERVER_PROFILES.get(expected_service) if expected_service else None
        effective_expected_protocol = expected_protocol_version or (profile.expected_protocol_version if profile and profile.require_protocol_version else None)

        raw_protocol = payload.get("protocolVersion") or payload.get("version")
        if effective_expected_protocol and not raw_protocol:
            raise ServerProtocolMismatchError("Server did not report a protocol version (Fail-Closed).")
        proto_ver = str(raw_protocol or "")
        if effective_expected_protocol and proto_ver != effective_expected_protocol:
            raise ServerProtocolMismatchError(f"Protocol version mismatch: expected '{effective_expected_protocol}', got '{proto_ver}'.")

        model_info = payload.get("model", {})
        if isinstance(model_info, str):
            model_info = {"id": model_info}
        elif not isinstance(model_info, dict):
            model_info = {}

        actual_model_id = model_info.get("id")
        actual_sha256 = model_info.get("sha256")
        discovered_model_ids: set[str] = set()

        # P1-1 & P1-2 & P0-2: Mandatory /v1/models capability query for models & profiles
        must_query_models = bool(profile and profile.require_model_endpoint)
        should_query_models = must_query_models or (not actual_model_id and (expected_model_id or require_model_identity))

        if should_query_models:
            models_url = f"{endpoint_url.rstrip('/')}/v1/models"
            req_m = urllib.request.Request(models_url, headers={"Accept": "application/json"})
            try:
                with opener.open(req_m, timeout=min(timeout_seconds, 5.0)) as resp_m:
                    if resp_m.status != 200:
                        if must_query_models:
                            raise ServerProtocolMismatchError(f"Models endpoint returned non-200 HTTP status: {resp_m.status}.")
                    else:
                        raw_m = resp_m.read(max_health_bytes + 1)
                        if len(raw_m) > max_health_bytes:
                            raise ServerProtocolMismatchError("Models response exceeds maximum allowed size.")
                        try:
                            m_data = json.loads(raw_m.decode("utf-8"))
                        except Exception as ex_j:
                            raise ServerProtocolMismatchError("Models response is not valid JSON (Fail-Closed).") from ex_j

                        if not isinstance(m_data, dict):
                            raise ServerProtocolMismatchError("Models response payload must be a JSON object.")

                        data_list = m_data.get("data", [])
                        if isinstance(data_list, list):
                            discovered_model_ids = {
                                item.get("id")
                                for item in data_list
                                if isinstance(item, dict) and isinstance(item.get("id"), str)
                            }
            except (ServerProtocolMismatchError, ServerConnectionRefusedError):
                raise
            except Exception as ex:
                if must_query_models:
                    raise ServerProtocolMismatchError(f"Mandatory models endpoint query failed for service '{expected_service}': {str(ex)}")

        # P0-2: Service identity capability match
        if expected_service:
            if service_id == expected_service:
                pass  # Direct assertion match
            elif expected_service == "openai-compatible" and service_id in allowed_services:
                pass  # Generic openai-compatible requirement is satisfied by any recognized backend
            elif service_id == "openai-compatible" and expected_service in {"llama-server", "bitnet-server"}:
                # Upstream server does not self-assert service name in /health, but provides capability
                if must_query_models and not discovered_model_ids and not actual_model_id:
                    raise ServerProtocolMismatchError(
                        f"Server does not exhibit required '{expected_service}' capability (missing /v1/models enumeration)."
                    )
                service_id = expected_service
            else:
                raise ServerProtocolMismatchError(f"Service mismatch: expected '{expected_service}', got '{service_id}'.")

        # P0-2 & P1-3: Strict fail-closed model identity check across all discovered model IDs
        if expected_model_id:
            if actual_model_id:
                if actual_model_id != expected_model_id and expected_model_id not in discovered_model_ids:
                    raise ModelIdentityMismatchError(
                        f"Model ID mismatch: expected '{expected_model_id}', got '{actual_model_id}'."
                    )
                if actual_model_id != expected_model_id and expected_model_id in discovered_model_ids:
                    actual_model_id = expected_model_id
            else:
                if expected_model_id in discovered_model_ids:
                    actual_model_id = expected_model_id
                elif discovered_model_ids:
                    raise ModelIdentityMismatchError(
                        f"Model ID mismatch: expected '{expected_model_id}', available: {sorted(discovered_model_ids)}."
                    )
                else:
                    raise ModelIdentityMismatchError(
                        "Expected model ID was configured, but the server did not provide model identity."
                    )

        if expected_model_sha256:
            if not actual_sha256:
                raise ModelIdentityMismatchError(
                    "Expected model SHA-256 was configured, but the server did not provide a checksum."
                )
            if not hmac.compare_digest(actual_sha256.lower(), expected_model_sha256.lower()):
                raise ModelIdentityMismatchError("Model checksum mismatch.")

        if require_model_identity and not actual_model_id and not actual_sha256 and not discovered_model_ids:
            raise ModelIdentityMismatchError("Server did not report model identity while require_model_identity is True.")

        payload["service"] = service_id
        payload["protocolVersion"] = proto_ver
        payload["model"] = {"id": actual_model_id, "sha256": actual_sha256}
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
    """
    Sovereign Enterprise Local Agent Runtime (Progressive Disclosure & Facade API).
    
    Simple Usage (User-Friendly Facade):
        >>> from termux_aichain import LocalAgent
        >>> agent = LocalAgent()  # Connects to default http://127.0.0.1:8080
        >>> print(agent.run("What is the battery level?"))
        
        >>> agent = LocalAgent.local("qwen2.5-1.5b")  # Ensures local model server is running
        >>> print(agent.run("Hello from Termux Edge!"))

    Advanced Usage:
        >>> agent = LocalAgent.connect("http://127.0.0.1:8080", tools=[vibrate_device])
    """

    def __init__(
        self,
        endpoint_or_mode: Optional[str] = None,
        chat_model: Optional[BaseChatModel] = None,
        tools: Optional[Sequence[Union[Tool, Callable[..., Any]]]] = None,
        tool_policy: Optional[ToolPolicy] = None,
        system_prompt: Optional[str] = None,
        managed_process: Optional[subprocess.Popen] = None,
        lock_file_path: Optional[Path] = None,
        lock_handle: Optional[Any] = None,
        owns_managed_process: bool = False,
        owns_identity_lock: bool = False,
        runtime_ownership: str = "OWNED",
        idle_timeout_seconds: float = 300.0,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        api_key: Optional[str] = None,
        mode: Optional[str] = None,
        **kwargs: Any
    ):
        # 1. Resolve mode and chat model with intuitive progressive defaults
        resolved_mode = mode or "connect"
        target_endpoint = "http://127.0.0.1:8080"

        if endpoint_or_mode:
            if endpoint_or_mode in {"connect", "managed", "embedded", "remote"}:
                resolved_mode = endpoint_or_mode
            else:
                target_endpoint = endpoint_or_mode
                resolved_mode = "connect"

        if chat_model is None:
            model_name = "default"
            chat_model = OpenAICompatibleChat(
                base_url=f"{target_endpoint.rstrip('/')}/v1",
                model=model_name,
                api_key=api_key
            )

        self.mode = resolved_mode
        self.chat_model = chat_model
        self.tools = list(tools or [])
        allow_registered = kwargs.get("allow_registered_tools", False)
        self.tool_policy = tool_policy or (
            ToolPolicy.allow_registered_tools_for_development([t.name if isinstance(t, Tool) else getattr(t, "__name__", "tool") for t in self.tools])
            if (allow_registered and self.tools) else ToolPolicy(default="deny")
        )
        self.system_prompt = system_prompt
        self.managed_process = managed_process
        self.lock_file_path = lock_file_path
        self.lock_handle = lock_handle
        self.owns_managed_process = owns_managed_process
        self.owns_identity_lock = owns_identity_lock
        self.runtime_ownership = runtime_ownership
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
            system_prompt=self.system_prompt,
            tool_policy=self.tool_policy,
            approval_callback=self.approval_callback
        )

        self._monitor_thread: Optional[threading.Thread] = None
        if self.mode == "managed" and self.owns_managed_process:
            self._monitor_thread = threading.Thread(target=self._idle_supervisor_loop, daemon=True)
            self._monitor_thread.start()

    @classmethod
    def connect(
        cls,
        endpoint: str = "http://127.0.0.1:8080",
        tools: Optional[Sequence[Union[Tool, Callable[..., Any]]]] = None,
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tool_policy: Optional[ToolPolicy] = None,
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ) -> LocalAgent:
        """User-friendly facade for connecting to any running local/remote model server."""
        return cls.create(
            mode="connect",
            endpoint=endpoint,
            tools=tools or [],
            api_key=api_key,
            system_prompt=system_prompt,
            tool_policy=tool_policy,
            approval_callback=approval_callback
        )

    @classmethod
    def local(
        cls,
        model: str = "qwen2.5-1.5b",
        tools: Optional[Sequence[Union[Tool, Callable[..., Any]]]] = None,
        system_prompt: Optional[str] = None,
        runtime_options: Optional[Dict[str, Any]] = None
    ) -> LocalAgent:
        """
        User-friendly 1-Line facade: Automatically inspects local model, connects to existing
        server if alive, or starts managed daemon server seamlessly.
        """
        # Resolve model path
        models_dir = Path.home() / "models"
        candidate_paths = [
            models_dir / f"{model}.gguf",
            models_dir / f"{model}-instruct-q4_k_m.gguf",
            models_dir / f"Qwen2.5-1.5B-Instruct-Q4_K_M.gguf",
            models_dir / f"Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            Path(model)
        ]
        resolved_path = None
        for p in candidate_paths:
            if p.exists() and p.is_file():
                resolved_path = p
                break

        endpoint = "http://127.0.0.1:8080"
        expected_id = resolved_path.name if resolved_path else model
        # Check if server is already running with the expected model identity
        try:
            ServerIdentityVerifier.verify(
                endpoint_url=endpoint,
                timeout_seconds=1.0,
                expected_service="llama-server",
                expected_model_id=expected_id
            )
            # Server is alive and verified -> Connect safely via standard validated pipeline
            return cls.create(
                mode="connect",
                endpoint=endpoint,
                connect=ConnectConfig(
                    expected_service="llama-server",
                    expected_model_id=expected_id
                ),
                tools=tools or [],
                system_prompt=system_prompt
            )
        except ServerConnectionRefusedError as _probe_err:
            # Server is not running -> Log probe status and proceed to managed daemon spawn
            import logging as _logging
            _logging.getLogger("termux_aichain.agent.auto").debug(
                "Probe to %s failed (%s); proceeding to managed daemon spawn.", endpoint, _probe_err
            )
        except (ServerProtocolMismatchError, ModelIdentityMismatchError) as exc:
            raise DuplicateServerOwnershipError(
                f"Existing server at {endpoint} conflicts with requested model '{expected_id}': {str(exc)}"
            ) from exc

        if not resolved_path:
            raise FileNotFoundError(
                f"Model '{model}' was not found in ~/models and no verified compatible server is running at {endpoint}."
            )

        return cls.create(
            mode="managed",
            model_path=str(resolved_path),
            tools=tools or [],
            system_prompt=system_prompt
        )

    def run(self, prompt_or_input: Union[str, Dict[str, Any]], max_iterations: int = 10) -> str:
        """
        High-level execution facade returning clean text response.
        
        >>> agent = LocalAgent()
        >>> print(agent.run("Summarize system status"))
        """
        if isinstance(prompt_or_input, str):
            input_payload = {"messages": [HumanMessage(prompt_or_input)]}
        else:
            input_payload = prompt_or_input

        res = self.invoke(input_payload, max_iterations=max_iterations)
        messages = res.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                return str(last_msg.content)
            elif isinstance(last_msg, dict):
                return str(last_msg.get("content", ""))
        return str(res)

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
                "runtime_ownership": self.runtime_ownership,
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
                _lock_errors: list = []
                try:
                    if fcntl:
                        fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
                    elif msvcrt:
                        self.lock_handle.seek(0)
                        msvcrt.locking(self.lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                    self.lock_handle.close()
                except OSError as _lock_err:
                    # 잠금 해제 실패 — 파일 디스크립터가 이미 닫혔거나 플랫폼 문제.
                    # 오류를 보존하되 종료 흐름은 계속 진행.
                    _lock_errors.append(f"lock_release_failed: {_lock_err}")
                    import logging as _logging
                    _logging.getLogger("termux_aichain.agent").warning(
                        "[agent] Lock release failed (degraded cleanup): %s", _lock_err
                    )
                except (AttributeError, ValueError) as _fd_err:
                    _lock_errors.append(f"lock_fd_error: {_fd_err}")
                    import logging as _logging
                    _logging.getLogger("termux_aichain.agent").warning(
                        "[agent] Lock FD error during cleanup: %s", _fd_err
                    )
                self.lock_handle = None
                if _lock_errors:
                    # degraded 상태 기록 — stopped이나 lock cleanup 미완료
                    import logging as _logging
                    _logging.getLogger("termux_aichain.agent").error(
                        "[agent] Identity lock cleanup incomplete. Agent may leave stale lock. errors=%s",
                        _lock_errors,
                    )

            if self.lock_file_path and self.lock_file_path.exists():
                try:
                    self.lock_file_path.unlink()
                except (PermissionError, OSError) as _unlink_err:
                    # 잠금 파일 삭제 실패 — 보안 cleanup 미완료.
                    # Exit Code 0을 반환하지 않도록 호출자에게 경고를 전달해야 함.
                    import logging as _logging
                    _logging.getLogger("termux_aichain.agent").error(
                        "[agent] SECURITY: Failed to remove lock file %s: %s. "
                        "Stale lock may prevent future process launches.",
                        self.lock_file_path, _unlink_err,
                    )



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
        approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        api_key: Optional[str] = None,
        **kwargs: Any
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

            server_info = ServerIdentityVerifier.verify(
                endpoint_url=target_endpoint,
                timeout_seconds=cfg.timeout_seconds,
                max_health_bytes=cfg.max_health_bytes,
                expected_service=cfg.expected_service,
                expected_protocol_version=cfg.expected_protocol_version or cfg.protocol_version,
                expected_model_id=cfg.expected_model_id,
                expected_model_sha256=cfg.expected_model_sha256
            )

            chat = OpenAICompatibleChat(
                base_url=f"{target_endpoint.rstrip('/')}/v1",
                model=cfg.expected_model_id or "default",
                api_key=api_key
            )
            return cls(
                mode="connect",
                chat_model=chat,
                tools=tools_list,
                tool_policy=tool_policy,
                system_prompt=system_prompt,
                owns_managed_process=False,
                owns_identity_lock=False,
                approval_callback=approval_callback,
                api_key=api_key
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
                    raise LocalAgentError("No supported OS file-lock backend (fcntl or msvcrt) is available.")
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

            server_mgr: Optional[Any] = None
            proc: Optional[subprocess.Popen] = None
            try:
                actual_threads = m_cfg.threads or max(1, (os.cpu_count() or 4) - 1)
                from termux_aichain.core.providers.local_server import LocalServerManager, LocalServerConfig
                srv_cfg = LocalServerConfig(
                    model_path=model_path,
                    host="127.0.0.1",
                    port=port,
                    threads=actual_threads,
                    n_ctx=m_cfg.n_ctx
                )
                server_mgr = LocalServerManager(srv_cfg, binary_name=m_cfg.binary_name)
                server_mgr.start(wait_ready=False)
                proc = server_mgr.process
                if proc is None:
                    raise ServerStartupTimeoutError("Managed server manager did not create a valid process.")

                t0 = time.time()
                ready = False
                while time.time() - t0 < m_cfg.startup_timeout_seconds:
                    if proc and proc.poll() is not None:
                        diagnostics = server_mgr.ring_log.get_recent_redacted_text(20)
                        raise ServerStartupTimeoutError(
                            f"Managed server exited prematurely with code {proc.returncode}.\n"
                            f"Recent Server Diagnostics:\n{diagnostics}"
                        )
                    status, _ = inspect_existing_server()
                    if status == "VERIFIED":
                        ready = True
                        break
                    time.sleep(0.5)

                if not ready:
                    diagnostics = server_mgr.ring_log.get_recent_redacted_text(20) if server_mgr else ""
                    raise ServerStartupTimeoutError(
                        f"Managed server failed to initialize within {m_cfg.startup_timeout_seconds}s.\n"
                        f"Recent Server Diagnostics:\n{diagnostics}"
                    )

                from termux_aichain.core.process_identity import get_process_start_identity
                target_pid = proc.pid if proc else os.getpid()
                start_ident = get_process_start_identity(target_pid)
                if not start_ident:
                    raise LocalAgentError(f"Unable to establish trustworthy process start identity for target process {target_pid}.")

                lock_meta = {
                    "schemaVersion": 1,
                    "pid": target_pid,
                    "startIdentity": start_ident,
                    "executablePath": shutil.which(m_cfg.binary_name) or m_cfg.binary_name,
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
                import logging as _logging
                _cleanup_logger = _logging.getLogger("termux_aichain.agent.create")
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    except OSError as _wait_err:
                        _cleanup_logger.warning("[agent.create] proc.wait failed: %s", _wait_err)
                if lock_handle:
                    try:
                        if fcntl:
                            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                        elif msvcrt:
                            lock_handle.seek(0)
                            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
                        lock_handle.close()
                    except (OSError, AttributeError, ValueError) as _lock_err:
                        _cleanup_logger.warning("[agent.create] Lock cleanup failed: %s", _lock_err)
                if lock_file.exists():
                    try:
                        lock_file.unlink()
                    except (PermissionError, OSError) as _unlink_err:
                        _cleanup_logger.error(
                            "[agent.create] SECURITY: Failed to remove lock file %s: %s",
                            lock_file, _unlink_err,
                        )
                raise  # 원래 예외를 반드시 재발생 — 성공으로 변환 금지



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