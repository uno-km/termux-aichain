import os
import time
import pytest
from termux_aichain import (
    LocalAgent,
    ConnectConfig,
    ManagedConfig,
    EmbeddedConfig,
    RemoteConfig,
    ToolPolicy,
    ToolRule,
    AgentState,
    vibrate_device,
    get_battery_status,
    HumanMessage,
    ServerConnectionRefusedError,
    RemoteFallbackNotAuthorizedError,
    ToolApprovalRequiredError,
    ToolArgumentValidationError,
    ToolRateLimitExceededError,
    NativeBackendUnavailableError
)
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import AIMessage, GenerationResult

class RuleBasedModel(BaseChatModel):
    def generate(self, messages):
        return GenerationResult(
            content='Action: termux_vibrate\nAction Input: {"duration_ms": 500}',
            message=AIMessage(content='Action: termux_vibrate\nAction Input: {"duration_ms": 500}')
        )

def test_connect_mode_loopback_policy():
    # Attempting to connect to external unauthorized domain with loopback_only policy
    with pytest.raises(ServerConnectionRefusedError) as exc_info:
        LocalAgent.create(
            mode="connect",
            endpoint="http://192.168.1.100:8080",
            connect=ConnectConfig(transport_policy="loopback_only", timeout_seconds=1.0)
        )
    assert "loopback_only" in str(exc_info.value)

def test_embedded_mode_contract():
    # Embedded mode should raise explicit contract error without compiled C/FFI
    with pytest.raises(NativeBackendUnavailableError) as exc_info:
        LocalAgent.create(mode="embedded", embedded=EmbeddedConfig(backend="vulkan"))
    assert "Embedded native C/FFI" in str(exc_info.value)

def test_remote_mode_explicit_opt_in():
    # Remote mode should reject un-enabled fallback
    with pytest.raises(RemoteFallbackNotAuthorizedError):
        LocalAgent.create(mode="remote", remote=RemoteConfig(enabled=False))

def test_tool_policy_range_validation():
    agent = LocalAgent(
        mode="test",
        chat_model=RuleBasedModel(),
        tools=[vibrate_device],
        tool_policy=ToolPolicy(
            default="allow",
            allowed_tools={
                "termux_vibrate": ToolRule(
                    allowed_ranges={"duration_ms": (50, 2000)}
                )
            }
        )
    )

    # Calling with invalid out-of-range argument
    with pytest.raises(ToolArgumentValidationError):
        agent._wrap_tool_with_policy(vibrate_device)(duration_ms=5000)

def test_tool_policy_rate_limiter():
    agent = LocalAgent(
        mode="test",
        chat_model=RuleBasedModel(),
        tools=[vibrate_device],
        tool_policy=ToolPolicy(
            default="allow",
            allowed_tools={
                "termux_vibrate": ToolRule(max_calls_per_minute=2)
            }
        )
    )

    guarded = agent._wrap_tool_with_policy(vibrate_device)
    guarded(duration_ms=100)
    guarded(duration_ms=100)
    # Third call within minute should trip rate limiter
    with pytest.raises(ToolRateLimitExceededError):
        guarded(duration_ms=100)

def test_tool_policy_approval_callback():
    approved_flag = False
    def approval_handler(tool_name, args):
        return approved_flag

    agent = LocalAgent(
        mode="test",
        chat_model=RuleBasedModel(),
        tools=[vibrate_device],
        tool_policy=ToolPolicy(
            default="allow",
            allowed_tools={
                "termux_vibrate": ToolRule(approval="explicit_prompt")
            }
        ),
        approval_callback=approval_handler
    )

    guarded = agent._wrap_tool_with_policy(vibrate_device)
    with pytest.raises(ToolApprovalRequiredError):
        guarded(duration_ms=100)

def test_status_state_machine():
    agent = LocalAgent(
        mode="test",
        chat_model=RuleBasedModel(),
        tools=[get_battery_status],
        idle_timeout_seconds=300.0
    )
    st = agent.status()
    assert st["mode"] == "test"
    assert st["state"] == "READY"
    assert "termux_battery_status" in st["tools_registered"]