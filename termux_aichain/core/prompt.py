"""
==============================================================================
termux-aichain Core Engine: PromptTemplate & Prompt Formatting
==============================================================================
Provides standard variable substitution and chat prompt assembly with
zero external heavy dependencies (Pure Python 3.10+ standard library).
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Union
from termux_aichain.core.base import Runnable
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, SystemMessage

_VAR_REGEX = re.compile(r"(?<!\{)\{([a-zA-Z0-9_]+)\}(?!\})")

class PromptTemplate(Runnable):
    """Zero-dependency string prompt template supporting named variable formatting."""

    def __init__(
        self,
        template: str,
        input_variables: Optional[List[str]] = None,
        partial_variables: Optional[Dict[str, Any]] = None
    ):
        self.template = template
        if input_variables is None:
            # Extract variables while ignoring escaped {{...}}
            # Replace {{ with dummy and }} with dummy temporarily for extraction
            cleaned = self.template.replace("{{", "").replace("}}", "")
            found = _VAR_REGEX.findall(cleaned)
            # Deduplicate preserving order
            seen = set()
            self.input_variables = [x for x in found if not (x in seen or seen.add(x))]
        else:
            self.input_variables = input_variables

        self.partial_variables = partial_variables or {}

    @classmethod
    def from_template(cls, template: str, partial_variables: Optional[Dict[str, Any]] = None) -> PromptTemplate:
        return cls(template=template, partial_variables=partial_variables)

    def format(self, **kwargs: Any) -> str:
        merged = {**self.partial_variables, **kwargs}
        missing = [v for v in self.input_variables if v not in merged]
        if missing:
            raise KeyError(f"Missing required prompt variables: {missing}")
        
        # Safe format handling literal {{ and }}
        res = self.template
        # Temporarily replace {{ with unique token and }} with unique token
        placeholder_open = "__DOUBLE_OPEN_BRACE__"
        placeholder_close = "__DOUBLE_CLOSE_BRACE__"
        res = res.replace("{{", placeholder_open).replace("}}", placeholder_close)
        
        for k in merged.keys():
            res = res.replace(f"{{{k}}}", str(merged[k]))
            
        res = res.replace(placeholder_open, "{").replace(placeholder_close, "}")
        return res

    def partial(self, **kwargs: Any) -> PromptTemplate:
        new_partial = {**self.partial_variables, **kwargs}
        remaining_vars = [v for v in self.input_variables if v not in new_partial]
        return PromptTemplate(
            template=self.template,
            input_variables=remaining_vars,
            partial_variables=new_partial
        )

    def invoke(self, input_data: Union[Dict[str, Any], str], **kwargs: Any) -> str:
        if isinstance(input_data, str):
            if len(self.input_variables) == 1:
                return self.format(**{self.input_variables[0]: input_data})
            return self.format(input=input_data)
        elif isinstance(input_data, dict):
            return self.format(**input_data)
        raise ValueError(f"PromptTemplate expects dict or string input, got: {type(input_data)}")

class ChatPromptTemplate(Runnable):
    """Zero-dependency Chat Prompt formatter assembling lists of Message objects."""

    def __init__(self, messages: List[tuple[str, str]]):
        self.message_templates = messages
        all_vars = []
        for role, tpl in messages:
            cleaned = tpl.replace("{{", "").replace("}}", "")
            found = _VAR_REGEX.findall(cleaned)
            all_vars.extend(found)
        seen = set()
        self.input_variables = [x for x in all_vars if not (x in seen or seen.add(x))]

    @classmethod
    def from_messages(cls, messages: List[tuple[str, str]]) -> ChatPromptTemplate:
        return cls(messages=messages)

    def format_messages(self, **kwargs: Any) -> List[Message]:
        result_messages: List[Message] = []
        placeholder_open = "__DOUBLE_OPEN_BRACE__"
        placeholder_close = "__DOUBLE_CLOSE_BRACE__"
        
        for role, tpl in self.message_templates:
            formatted = tpl.replace("{{", placeholder_open).replace("}}", placeholder_close)
            for k, v in kwargs.items():
                formatted = formatted.replace(f"{{{k}}}", str(v))
            formatted = formatted.replace(placeholder_open, "{").replace(placeholder_close, "}")

            r = role.lower().strip()
            if r in ("system", "sys"):
                result_messages.append(SystemMessage(content=formatted))
            elif r in ("human", "user"):
                result_messages.append(HumanMessage(content=formatted))
            elif r in ("ai", "assistant"):
                result_messages.append(AIMessage(content=formatted))
            else:
                result_messages.append(Message(role=role, content=formatted))

        return result_messages

    def invoke(self, input_data: Union[Dict[str, Any], str], **kwargs: Any) -> List[Message]:
        if isinstance(input_data, str):
            return self.format_messages(input=input_data)
        elif isinstance(input_data, dict):
            return self.format_messages(**input_data)
        raise ValueError(f"ChatPromptTemplate expects dict or string input, got: {type(input_data)}")