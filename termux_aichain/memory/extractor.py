"""
==============================================================================
termux-aichain Memory Engine: Fact Extractor
==============================================================================
Automatically extracts key facts from conversations into persistent memory.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.prompt import PromptTemplate
from termux_aichain.core.parsers import JsonOutputParser
from termux_aichain.memory.sqlite import SQLiteEntityMemory

_EXTRACTION_PROMPT = """Extract permanent user facts, device configurations, or preferences from the conversation text.
Format output strictly as a JSON object with key-value pairs (e.g. {{"user_name": "Uno", "preferred_device": "Galaxy S20"}}).
If no clear facts are found, return {{}}.

Conversation Text:
{text}
"""

class FactExtractor:
    """Extracts facts from text and saves them into an SQLiteEntityMemory instance."""

    def __init__(self, model: BaseChatModel, memory: Optional[SQLiteEntityMemory] = None):
        self.model = model
        self.memory = memory or SQLiteEntityMemory()
        self.parser = JsonOutputParser(default_factory=dict)
        self.prompt = PromptTemplate.from_template(_EXTRACTION_PROMPT)
        self.chain = self.prompt | self.model | self.parser

    def extract_and_save(self, text: str) -> Dict[str, Any]:
        extracted: Dict[str, Any] = self.chain.invoke({"text": text})
        if isinstance(extracted, dict):
            for k, v in extracted.items():
                self.memory.set(str(k), v)
        return extracted