"""
==============================================================================
termux-aichain Core Structured Output Parsers
==============================================================================
Provides robust, zero-dependency output parsers for extracting JSON, structured
objects, and string payloads from model generation results.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
import json
from typing import Any, Dict, List, Optional, Pattern, Union
from termux_aichain.core.schema import Message, AIMessage, GenerationResult, StreamChunk
from termux_aichain.core.base import Runnable

class BaseOutputParser(Runnable):
    """Abstract base class for all output parsers."""

    def invoke(self, input_val: Any, **kwargs: Any) -> Any:
        text = self._extract_text(input_val)
        return self.parse(text)

    def _extract_text(self, input_val: Any) -> str:
        if isinstance(input_val, str):
            return input_val
        elif isinstance(input_val, GenerationResult):
            return input_val.content
        elif isinstance(input_val, Message):
            return input_val.content
        elif isinstance(input_val, StreamChunk):
            return input_val.content
        return str(input_val)

    def parse(self, text: str) -> Any:
        raise NotImplementedError

class StringOutputParser(BaseOutputParser):
    """Parses generation output into clean stripped text."""

    def __init__(self, strip: bool = True):
        self.strip = strip

    def parse(self, text: str) -> str:
        return text.strip() if self.strip else text

    def __repr__(self) -> str:
        return "StringOutputParser()"

_JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

class JsonOutputParser(BaseOutputParser):
    """Extracts and parses JSON object or array from markdown blocks or raw text."""

    def __init__(self, default_factory: Optional[Any] = None):
        self.default_factory = default_factory

    def parse(self, text: str) -> Any:
        cleaned = text.strip()

        # 1. Try markdown code block match
        match = _JSON_BLOCK_REGEX.search(cleaned)
        if match:
            target_str = match.group(1).strip()
            try:
                return json.loads(target_str)
            except json.JSONDecodeError:
                pass  # Allowed: next strategy follows. Final failure re-raises at L99.

        # 2. Try direct full-text JSON load
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass  # Allowed: next strategy follows.

        # 3. Try to locate outermost {...} or [...]
        start_obj = cleaned.find("{")
        end_obj = cleaned.rfind("}")
        start_arr = cleaned.find("[")
        end_arr = cleaned.rfind("]")

        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            candidate = cleaned[start_obj:end_obj + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass  # Allowed: next strategy follows.

        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            candidate = cleaned[start_arr:end_arr + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass  # Allowed: final strategy. ValueError raised below if all fail.

        if self.default_factory is not None:
            return self.default_factory() if callable(self.default_factory) else self.default_factory

        raise ValueError(f"Failed to parse JSON from generation output:\n{text}")



    def __repr__(self) -> str:
        return "JsonOutputParser()"

class RegexOutputParser(BaseOutputParser):
    """Extracts groups matching a regular expression."""

    def __init__(self, regex: Union[str, Pattern[str]], group: Optional[Union[int, str]] = None):
        self.regex = re.compile(regex) if isinstance(regex, str) else regex
        self.group = group

    def parse(self, text: str) -> Any:
        match = self.regex.search(text)
        if not match:
            raise ValueError(f"Regex pattern {self.regex.pattern} did not match text: {text}")
        if self.group is not None:
            return match.group(self.group)
        groupdict = match.groupdict()
        if groupdict:
            return groupdict
        groups = match.groups()
        if groups:
            return groups if len(groups) > 1 else groups[0]
        return match.group(0)

    def __repr__(self) -> str:
        return f"RegexOutputParser(pattern='{self.regex.pattern}')"