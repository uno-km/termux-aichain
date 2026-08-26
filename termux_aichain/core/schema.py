"""
==============================================================================
termux-aichain Core Schema
==============================================================================
Defines the standard message types, token usage structures, and generation
results for lightweight edge agent workflows.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal, Union

RoleType = Literal["system", "user", "assistant", "tool", "function"]

class Message:
    def __init__(
        self,
        role: RoleType,
        content: str,
        name: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        additional_kwargs: Optional[Dict[str, Any]] = None
    ):
        self.role: RoleType = role
        self.content: str = content
        self.name: Optional[str] = name
        self.tool_calls: Optional[List[Dict[str, Any]]] = tool_calls
        self.additional_kwargs: Dict[str, Any] = additional_kwargs or {}

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.additional_kwargs:
            d["additional_kwargs"] = self.additional_kwargs
        return d

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(role='{self.role}', content={self.content!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Message):
            return False
        return (
            self.role == other.role
            and self.content == other.content
            and self.name == other.name
            and self.tool_calls == other.tool_calls
        )

class SystemMessage(Message):
    def __init__(self, content: str, name: Optional[str] = None, **kwargs: Any):
        super().__init__(role="system", content=content, name=name, additional_kwargs=kwargs)

class HumanMessage(Message):
    def __init__(self, content: str, name: Optional[str] = None, **kwargs: Any):
        super().__init__(role="user", content=content, name=name, additional_kwargs=kwargs)

class AIMessage(Message):
    def __init__(self, content: str, name: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None, **kwargs: Any):
        super().__init__(role="assistant", content=content, name=name, tool_calls=tool_calls, additional_kwargs=kwargs)

class ToolMessage(Message):
    def __init__(self, content: str, tool_call_id: Optional[str] = None, name: Optional[str] = None, **kwargs: Any):
        super().__init__(role="tool", content=content, name=name, additional_kwargs=kwargs)
        self.tool_call_id = tool_call_id

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        return d

@dataclass
class UsageInfo:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0

@dataclass
class GenerationResult:
    content: str
    message: AIMessage
    usage: UsageInfo = field(default_factory=UsageInfo)
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.content

@dataclass
class StreamChunk:
    content: str
    delta: str
    is_last: bool = False
    usage: Optional[UsageInfo] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.delta