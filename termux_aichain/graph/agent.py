"""
==============================================================================
termux-aichain Graph Engine: Tool Calling & ReAct Agent Factory
==============================================================================
Provides zero-dependency Tool abstractions and autonomous ReAct agent graphs.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import json
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Union
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, SystemMessage, ToolMessage
from termux_aichain.core.base import BaseChatModel
from termux_aichain.graph.state import StateGraph, START, END, CompiledGraph

@dataclass
class Tool:
    """Zero-dependency Tool definition interface for model tool calling."""
    name: str
    description: str
    func: Callable[..., Any]
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)

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

def tool(name: Optional[str] = None, description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator to define a Tool from a Python function."""
    def decorator(fn: Callable[..., Any]) -> Tool:
        tool_name = name or fn.__name__
        tool_doc = description or (fn.__doc__ or "").strip() or f"Executes {tool_name}"
        return Tool(name=tool_name, description=tool_doc, func=fn, parameters=parameters or {})
    return decorator

def create_react_agent(
    model: BaseChatModel,
    tools: Sequence[Tool],
    system_prompt: Optional[str] = None
) -> CompiledGraph:
    """Compiles a cyclic ReAct (Reasoning + Tool Acting) Agent using StateGraph."""
    tools_by_name = {t.name: t for t in tools}

    def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = list(state.get("messages", []))
        if system_prompt and not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages

        gen_result = model.generate(messages)
        ai_msg = gen_result.message
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
            func_info = call.get("function", {})
            fn_name = func_info.get("name")
            args_str = func_info.get("arguments", "{}")

            if isinstance(args_str, str):
                try:
                    fn_args = json.loads(args_str)
                except Exception:
                    fn_args = {}
            elif isinstance(args_str, dict):
                fn_args = args_str
            else:
                fn_args = {}

            if fn_name in tools_by_name:
                try:
                    tool_output = tools_by_name[fn_name](**fn_args)
                    tool_content = str(tool_output)
                except Exception as ex:
                    tool_content = f"Error executing tool {fn_name}: {str(ex)}"
            else:
                tool_content = f"Tool '{fn_name}' not found."

            new_tool_messages.append(ToolMessage(content=tool_content, tool_call_id=call_id, name=fn_name))

        return {"messages": messages + new_tool_messages}

    workflow = StateGraph()
    workflow.add_node("agent_node", agent_node)
    workflow.add_node("tools_node", tools_node)

    workflow.set_entry_point("agent_node")
    workflow.add_conditional_edges("agent_node", should_continue, {"tools_node": "tools_node", END: END})
    workflow.add_edge("tools_node", "agent_node")

    return workflow.compile()