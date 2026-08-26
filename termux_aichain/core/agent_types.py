"""
==============================================================================
termux-aichain LocalAgent: Typed Configuration, State Machine & Error Contract
==============================================================================
Provides enterprise-grade configuration schemas, state lifecycles, and
structured exception hierarchy for connect, managed, embedded, and remote modes.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

# ==============================================================================
# 1. Standard Error Contract
# ==============================================================================

class LocalAgentError(Exception):
    """Base exception for all LocalAgent and runtime failures."""
    pass

class ServerConnectionRefusedError(LocalAgentError):
    """Raised when connect mode cannot establish connection to target endpoint."""
    pass

class ServerProtocolMismatchError(LocalAgentError):
    """Raised when server protocol version or service identity is incompatible."""
    pass

class ModelIdentityMismatchError(LocalAgentError):
    """Raised when target model SHA256 or ID does not match expected identity."""
    pass

class ManagedSpawnNotSupportedError(LocalAgentError):
    """Raised when current platform environment restricts child process execution."""
    pass

class ServerStartupTimeoutError(LocalAgentError):
    """Raised when managed server process fails to become healthy within deadline."""
    pass

class DuplicateServerOwnershipError(LocalAgentError):
    """Raised when another process holds the identity lock and conflict cannot resolve."""
    pass

class RemoteFallbackNotAuthorizedError(LocalAgentError):
    """Raised when remote delegation is attempted without explicit opt-in policy."""
    pass

class ToolApprovalRequiredError(LocalAgentError):
    """Raised when a sensitive tool is invoked without mandatory user approval."""
    pass

class ToolArgumentValidationError(LocalAgentError):
    """Raised when tool input arguments violate schema constraints or value ranges."""
    pass

class ToolRateLimitExceededError(LocalAgentError):
    """Raised when tool invocation frequency exceeds max_calls_per_minute quota."""
    pass

class ToolPolicyDeniedError(LocalAgentError):
    """Raised when a tool is not explicitly permitted under default deny policy."""
    pass

class ToolCallRepairNotAllowedError(LocalAgentError):
    """Raised when a tool call JSON required syntax repair, strictly forbidden for hardware actuation."""
    pass

class DuplicateToolAliasError(LocalAgentError):
    """Raised when a tool declares an alias that conflicts with an existing tool."""
    pass

class NativeBackendUnavailableError(LocalAgentError):
    """Raised when embedded C/FFI runtime is missing or ABI version mismatches."""
    pass


# ==============================================================================
# 2. Common Agent Lifecycle State Machine
# ==============================================================================

class AgentState(str, enum.Enum):
    """Unified state lifecycle across all 4 execution modes."""
    NEW = "NEW"
    STARTING = "STARTING"
    VERIFYING = "VERIFYING"
    READY = "READY"
    BUSY = "BUSY"
    IDLE = "IDLE"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RESTART_BACKOFF = "RESTART_BACKOFF"


# ==============================================================================
# 3. Typed Configuration Schemas
# ==============================================================================

@dataclass(frozen=True)
class ToolCallCandidate:
    """Unvalidated tool call candidate extracted from raw model output."""
    id: str
    name: str
    arguments: Dict[str, Any]
    source: str
    repaired: bool = False
    schema_validated: bool = False
    policy_authorized: bool = False


@dataclass
class TransportSecurityConfig:
    """Security policy for network and loopback bindings."""
    policy: str = "loopback_only"  # "loopback_only", "unix_socket", "tls_required", "private_network_with_mtls"
    certificate_pin: Optional[str] = None
    credential_provider: Optional[Callable[[], Dict[str, str]]] = None


@dataclass
class ConnectConfig:
    """Explicit configuration for externally supervised servers."""
    expected_service: str = "openai-compatible"
    expected_protocol_version: Optional[str] = None
    expected_model_id: Optional[str] = None
    expected_model_sha256: Optional[str] = None
    transport_policy: str = "loopback_only"
    protocol_version: Optional[str] = None
    startup_process_allowed: bool = False
    timeout_seconds: float = 15.0
    max_health_bytes: int = 65536


@dataclass
class ManagedConfig:
    """Configuration for SDK-supervised child server processes."""
    idle_timeout_seconds: float = 300.0
    startup_timeout_seconds: float = 30.0
    max_restarts: int = 2
    loopback_only: bool = True
    orphan_lease_timeout_seconds: float = 45.0
    threads: Optional[int] = None
    n_ctx: int = 2048
    n_gpu_layers: int = 0
    binary_name: str = "llama-server"


@dataclass
class EmbeddedConfig:
    """Configuration for in-process native model runtime."""
    backend: str = "cpu"  # "cpu", "vulkan", "opencl", "nnapi"
    n_threads: int = 4
    context_size: int = 2048
    allow_native_crash_boundary: bool = True


@dataclass
class RemoteConfig:
    """Configuration for explicit remote inference fallback."""
    enabled: bool = False
    endpoint: Optional[str] = None
    allowed_data_classes: List[str] = field(default_factory=lambda: ["PUBLIC", "NON_SENSITIVE"])
    require_user_consent: bool = True
    redact_before_send: bool = True
    timeout_seconds: float = 20.0
    monthly_cost_limit_usd: float = 10.0


@dataclass
class ToolRule:
    """Per-tool security and quota constraint."""
    approval: str = "none"  # "none", "explicit_prompt", "token_verified"
    max_calls_per_minute: int = 60
    max_duration_ms: Optional[int] = None
    allowed_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)


@dataclass
class ToolPolicy:
    """Global tool execution policy and rate-limiting rules with fail-closed default."""
    default: str = "deny"  # Default is strictly "deny"
    allowed_tools: Dict[str, Union[ToolRule, Dict[str, Any]]] = field(default_factory=dict)
    enforce_schema_ranges: bool = True
    audit_redaction: bool = True

    @classmethod
    def allow_registered_tools_for_development(cls, tool_names: Sequence[str]) -> ToolPolicy:
        """Explicit opt-in helper for development and local testing only."""
        rules = {name: ToolRule(approval="none", max_calls_per_minute=120) for name in tool_names}
        return cls(default="allow", allowed_tools=rules)