"""
==============================================================================
termux-aichain Graph Engine: Tool Calling & ReAct Agent Factory
==============================================================================
Provides zero-dependency Tool abstractions and autonomous ReAct agent graphs.
Enforces strict JSON Schema validation and exact signature binding before execution.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
import json
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from termux_aichain.core.schema import Message, HumanMessage, AIMessage, SystemMessage, ToolMessage
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.agent_types import (
    DuplicateToolAliasError,
    ToolArgumentValidationError,
    ToolCallRepairNotAllowedError,
    ToolPolicy,
    ToolRule,
    ToolPolicyDeniedError,
    ToolRateLimitExceededError,
    ToolApprovalRequiredError,
)
from termux_aichain.graph.state import StateGraph, START, END, CompiledGraph
from termux_aichain.output.normalizer import OutputNormalizer, RawModelResponse, ToolCall, OutputParserPolicy, validate_tool_arguments

@dataclass
class Tool:
    """Zero-dependency Tool definition interface for model tool calling."""
    name: str
    description: str
    func: Callable[..., Any]
    parameters: Dict[str, Any] = field(default_factory=dict)
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

    def invoke(self, input_data: Any) -> Any:
        if isinstance(input_data, dict):
            return self.func(**input_data)
        elif isinstance(input_data, (tuple, list)):
            return self.func(*input_data)
        elif input_data is None:
            return self.func()
        else:
            return self.func(input_data)

    def to_openai_tool(self) -> Dict[str, Any]:
        """Converts to standard OpenAI Tool Calling specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    aliases: Tuple[str, ...] = ()
) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator to define a Tool from a Python function with explicit aliases."""
    def decorator(fn: Callable[..., Any]) -> Tool:
        tool_name = name or fn.__name__
        tool_doc = description or (fn.__doc__ or "").strip() or f"Executes {tool_name}"
        return Tool(name=tool_name, description=tool_doc, func=fn, parameters=parameters or {}, aliases=aliases)
    return decorator

def create_react_agent(
    model: Union[BaseChatModel, Callable[..., Any], Any],
    tools: Sequence[Union[Tool, Callable[..., Any]]],
    system_prompt: Optional[str] = None,
    parser_policy: Optional[OutputParserPolicy] = None,
    tool_policy: Optional[ToolPolicy] = None,
    approval_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
) -> CompiledGraph:
    """Compiles a cyclic ReAct Agent using StateGraph with strict alias collision checks, authorization policies, and normalization."""
    normalized_tools: List[Tool] = []
    for t in tools:
        if isinstance(t, Tool):
            normalized_tools.append(t)
        elif callable(t):
            t_name = getattr(t, "__name__", "tool")
            t_doc = (getattr(t, "__doc__", "") or f"Tool {t_name}").strip()
            normalized_tools.append(Tool(name=t_name, description=t_doc, func=t))

    # P0-9: Strict Alias Registry
    tools_by_name: Dict[str, Tool] = {}
    for t in normalized_tools:
        if t.name in tools_by_name:
            raise DuplicateToolAliasError(f"Duplicate primary tool name '{t.name}' registered.")
        tools_by_name[t.name] = t

        for alias in t.aliases:
            if alias in tools_by_name:
                raise DuplicateToolAliasError(f"Tool alias conflict: '{alias}' declared by '{t.name}' conflicts with '{tools_by_name[alias].name}'.")
            tools_by_name[alias] = t

    effective_policy = parser_policy or OutputParserPolicy()
    effective_tool_policy = tool_policy or ToolPolicy(
        default="deny",
        allowed_tools={t.name: ToolRule() for t in normalized_tools}
    )

    if system_prompt:
        effective_system_prompt = system_prompt
    else:
        tool_lines = [f"- {t.name}: {t.description}" for t in normalized_tools]
        effective_system_prompt = (
            "You are an Android assistant. When asked to perform hardware tasks, use this exact format:\n"
            "Action: <tool_name>\n"
            "Action Input: <json_arguments>\n\n"
            f"Available tools:\n" + "\n".join(tool_lines)
        )

    def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = list(state.get("messages", []))
        if effective_system_prompt and not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=effective_system_prompt)] + messages

        if hasattr(model, "generate"):
            gen_result = model.generate(messages)
            ai_msg = gen_result.message
        elif hasattr(model, "invoke"):
            resp = model.invoke(messages)
            if isinstance(resp, AIMessage):
                ai_msg = resp
            else:
                ai_msg = AIMessage(content=str(resp))
        elif callable(model):
            resp = model(messages)
            if isinstance(resp, AIMessage):
                ai_msg = resp
            else:
                ai_msg = AIMessage(content=str(resp))
        else:
            raise TypeError(f"Unsupported model type: {type(model)}")

        raw_response = RawModelResponse(
            provider="generic",
            model="agent_model",
            text=ai_msg.content or "",
            native_tool_calls=ai_msg.tool_calls
        )
        normalized = OutputNormalizer.normalize(raw_response, registered_tool_names=list(tools_by_name.keys()), policy=effective_policy)

        if normalized.type == "tool_call" and normalized.tool_calls:
            ai_msg.tool_calls = [{
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False) if isinstance(tc.arguments, dict) else str(tc.arguments)
                },
                "_repaired": tc.repaired
            } for tc in normalized.tool_calls]
        else:
            ai_msg.tool_calls = None
            if normalized.content is not None:
                ai_msg.content = normalized.content

        return {"messages": messages + [ai_msg], "last_ai_message": ai_msg}

    def should_continue(state: Dict[str, Any]) -> str:
        last_ai_msg: Optional[AIMessage] = state.get("last_ai_message")
        if not last_ai_msg or not last_ai_msg.tool_calls:
            return END
        return "tools_node"

    def tools_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = list(state.get("messages", []))
        last_ai_msg: AIMessage = state["last_ai_message"]
        tool_calls = last_ai_msg.tool_calls or []
        new_tool_messages: List[Message] = []

        for call in tool_calls:
            call_id = call.get("id", "call_id")
            is_repaired = call.get("_repaired", False)
            func_info = call.get("function", {})
            fn_name = func_info.get("name")
            args_str = func_info.get("arguments", "{}")

            if is_repaired:
                tool_content = f"Error executing tool '{fn_name}': ToolCallRepairNotAllowedError - Syntax repair is strictly forbidden for hardware actuation."
                new_tool_messages.append(ToolMessage(content=tool_content, tool_call_id=call_id))
                continue

            if isinstance(args_str, str):
                try:
                    fn_args = json.loads(args_str)
                except Exception:
                    fn_args = {"input": args_str} if args_str else {}
            elif isinstance(args_str, dict):
                fn_args = args_str
            else:
                fn_args = {}

            if fn_name in tools_by_name:
                try:
                    target_tool = tools_by_name[fn_name]

                    # 1. Tool Policy Check (Default Deny)
                    if effective_tool_policy.default == "deny" and fn_name not in effective_tool_policy.allowed_tools:
                        raise ToolPolicyDeniedError(f"Tool '{fn_name}' is denied by security policy (default=deny).")

                    rule_raw = effective_tool_policy.allowed_tools.get(fn_name, ToolRule())
                    rule = rule_raw if isinstance(rule_raw, ToolRule) else ToolRule(**rule_raw)

                    # 2. Strict Tool JSON Schema Validation before binding
                    if isinstance(fn_args, dict) and target_tool.parameters:
                        validate_tool_arguments(target_tool.parameters, fn_args)

                    # 3. Allowed ranges check
                    if isinstance(fn_args, dict):
                        for param_name, val in fn_args.items():
                            if param_name in rule.allowed_ranges:
                                min_val, max_val = rule.allowed_ranges[param_name]
                                if isinstance(val, bool):
                                    raise ToolArgumentValidationError(f"Argument '{param_name}' must be an integer, bool is rejected.")
                                if not isinstance(val, (int, float)) or not (min_val <= val <= max_val):
                                    raise ToolArgumentValidationError(
                                        f"Argument '{param_name}' value {val} violates allowed range [{min_val}, {max_val}]."
                                    )

                    # 4. User Approval Callback
                    if rule.approval in ("explicit_prompt", "token_verified"):
                        if not approval_callback:
                            raise ToolApprovalRequiredError(f"Tool '{fn_name}' requires approval but no callback was registered.")
                        if not approval_callback(fn_name, fn_args if isinstance(fn_args, dict) else {}):
                            raise ToolApprovalRequiredError(f"Invocation of tool '{fn_name}' was rejected by user approval.")

                    # 5. Strict Signature Binding (bind() instead of bind_partial())
                    sig = inspect.signature(target_tool.func)
                    if isinstance(fn_args, dict):
                        bound = sig.bind(**fn_args)
                        bound.apply_defaults()
                        tool_output = target_tool(*bound.args, **bound.kwargs)
                    else:
                        bound = sig.bind(fn_args)
                        bound.apply_defaults()
                        tool_output = target_tool(*bound.args, **bound.kwargs)
                    tool_content = str(tool_output)
                except Exception as ex:
                    tool_content = f"Error executing tool '{fn_name}': {str(ex)}"
            else:
                tool_content = f"Tool '{fn_name}' not found in registered tools."

            new_tool_messages.append(ToolMessage(content=tool_content, tool_call_id=call_id))

        return {"messages": messages + new_tool_messages}

    workflow = StateGraph()
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools_node", tools_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools_node", "agent")

    return workflow.compile()