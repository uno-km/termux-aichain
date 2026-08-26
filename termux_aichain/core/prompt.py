"""
==============================================================================
termux-aichain Core Prompt Templates
==============================================================================
Provides standard string and chat prompt formatting templates.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from termux_aichain.core.schema import Message, SystemMessage, HumanMessage, AIMessage, RoleType

_VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

def extract_variables(template_str: str) -> List[str]:
    """Extracts unique variable names enclosed in single curly braces."""
    return list(dict.fromkeys(_VARIABLE_PATTERN.findall(template_str)))

class PromptTemplate:
    """Standard string-based prompt template."""

    def __init__(self, template: str, input_variables: Optional[List[str]] = None, partial_variables: Optional[Dict[str, Any]] = None):
        self.template = template
        self.input_variables = input_variables if input_variables is not None else extract_variables(template)
        self.partial_variables = partial_variables or {}

    @classmethod
    def from_template(cls, template: str, **kwargs: Any) -> PromptTemplate:
        return cls(template=template, **kwargs)

    def partial(self, **kwargs: Any) -> PromptTemplate:
        new_partial = {**self.partial_variables, **kwargs}
        return PromptTemplate(
            template=self.template,
            input_variables=[v for v in self.input_variables if v not in new_partial],
            partial_variables=new_partial
        )

    def format(self, **kwargs: Any) -> str:
        merged = {**self.partial_variables, **kwargs}
        missing = [v for v in self.input_variables if v not in merged]
        if missing:
            raise KeyError(f"Missing required prompt variables: {missing}")
        return self.template.format(**merged)

    def format_prompt(self, **kwargs: Any) -> str:
        return self.format(**kwargs)

    def __repr__(self) -> str:
        return f"PromptTemplate(input_variables={self.input_variables})"

class MessagePromptTemplate:
    """Individual message template for ChatPromptTemplate."""

    def __init__(self, role: RoleType, prompt: PromptTemplate):
        self.role = role
        self.prompt = prompt

    @classmethod
    def from_template(cls, role: RoleType, template: str) -> MessagePromptTemplate:
        return cls(role=role, prompt=PromptTemplate.from_template(template))

    def format(self, **kwargs: Any) -> Message:
        text = self.prompt.format(**kwargs)
        if self.role == "system":
            return SystemMessage(content=text)
        elif self.role == "user":
            return HumanMessage(content=text)
        elif self.role == "assistant":
            return AIMessage(content=text)
        return Message(role=self.role, content=text)

class ChatPromptTemplate:
    """Chat message list template containing system, human, and AI messages."""

    def __init__(self, messages: Sequence[Union[MessagePromptTemplate, Message, Tuple[str, str]]]):
        self.message_templates: List[Union[MessagePromptTemplate, Message]] = []
        all_vars: List[str] = []

        for m in messages:
            if isinstance(m, tuple) and len(m) == 2:
                role, template_str = m
                tpl = MessagePromptTemplate.from_template(role=role, template=template_str)  # type: ignore
                self.message_templates.append(tpl)
                all_vars.extend(tpl.prompt.input_variables)
            elif isinstance(m, MessagePromptTemplate):
                self.message_templates.append(m)
                all_vars.extend(m.prompt.input_variables)
            elif isinstance(m, Message):
                self.message_templates.append(m)
            else:
                raise TypeError(f"Unsupported message template type: {type(m)}")

        self.input_variables: List[str] = list(dict.fromkeys(all_vars))

    @classmethod
    def from_messages(cls, messages: Sequence[Union[MessagePromptTemplate, Message, Tuple[str, str]]]) -> ChatPromptTemplate:
        return cls(messages=messages)

    def format_messages(self, **kwargs: Any) -> List[Message]:
        result: List[Message] = []
        for item in self.message_templates:
            if isinstance(item, MessagePromptTemplate):
                result.append(item.format(**kwargs))
            elif isinstance(item, Message):
                result.append(item)
        return result

    def format(self, **kwargs: Any) -> List[Message]:
        return self.format_messages(**kwargs)

    def __repr__(self) -> str:
        return f"ChatPromptTemplate(input_variables={self.input_variables}, message_count={len(self.message_templates)})"