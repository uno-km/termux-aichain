"""
==============================================================================
termux-aichain Graph Engine: Tool Calling & ReAct Agent Factory
==============================================================================
Provides zero-dependency Tool abstractions and autonomous ReAct agent graphs.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
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

def tool(name: Optional[str] = None, description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator to define a Tool from a Python function."""
    def decorator(fn: Callable[..., Any]) -> Tool:
        tool_name = name or fn.__name__
        tool_doc = description or (fn.__doc__ or "").strip() or f"Executes {tool_name}"
        return Tool(name=tool_name, description=tool_doc, func=fn, parameters=parameters or {})
    return decorator

def create_react_agent(
    model: Union[BaseChatModel, Callable[..., Any], Any],
    tools: Sequence[Union[Tool, Callable[..., Any]]],
    system_prompt: Optional[str] = None
) -> CompiledGraph:
    """Compiles a cyclic ReAct (Reasoning + Tool Acting) Agent using StateGraph."""
    normalized_tools: List[Tool] = []
    for t in tools:
        if isinstance(t, Tool):
            normalized_tools.append(t)
        elif callable(t):
            t_name = getattr(t, "__name__", "tool")
            t_doc = (getattr(t, "__doc__", "") or f"Tool {t_name}").strip()
            normalized_tools.append(Tool(name=t_name, description=t_doc, func=t))

    tools_by_name = {t.name: t for t in normalized_tools}

    def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        messages = list(state.get("messages", []))
        if system_prompt and not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=system_prompt)] + messages

        # Flexible model execution supporting BaseChatModel, invoke, generate, or callable
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

        # Fallback ReAct text parser for small edge models without native tool-calling JSON
        if not ai_msg.tool_calls and ai_msg.content:
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)", ai_msg.content)
            input_match = re.search(r"Action Input:\s*(\{.*?\}|\[.*?\]|[^\n]+)", ai_msg.content, re.DOTALL)
            if action_match:
                fn_name = action_match.group(1).strip()
                raw_args = input_match.group(1).strip() if input_match else "{}"
                ai_msg.tool_calls = [{
                    "id": f"call_{len(messages)}",
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": raw_args
                    }
                }]

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
                    fn_args = {"input": args_str} if args_str else {}
            elif isinstance(args_str, dict):
                fn_args = args_str
            else:
                fn_args = {}

            if fn_name in tools_by_name:
                try:
                    target_tool = tools_by_name[fn_name]
                    if isinstance(fn_args, dict):
                        # inspect parameter signature
                        sig = inspect.signature(target_tool.func)
                        if len(sig.parameters) == 0:
                            tool_output = target_tool()
                        else:
                            tool_output = target_tool(**fn_args)
                    else:
                        tool_output = target_tool(fn_args)
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