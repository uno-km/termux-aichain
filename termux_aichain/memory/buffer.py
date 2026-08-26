"""
==============================================================================
termux-aichain Memory Engine: Conversation Buffer Memory
==============================================================================
Provides short-term windowed conversation history management.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, SystemMessage

class ConversationBufferMemory:
    """Maintains a rolling window of recent conversation messages."""

    def __init__(self, k: int = 10, return_messages: bool = True, memory_key: str = "history"):
        self.k = k
        self.return_messages = return_messages
        self.memory_key = memory_key
        self.chat_history: List[Message] = []

    def save_context(self, inputs: Union[Dict[str, Any], str], outputs: Union[Dict[str, Any], str]) -> None:
        user_text = inputs if isinstance(inputs, str) else list(inputs.values())[0] if inputs else ""
        ai_text = outputs if isinstance(outputs, str) else list(outputs.values())[0] if outputs else ""

        self.chat_history.append(HumanMessage(content=str(user_text)))
        self.chat_history.append(AIMessage(content=str(ai_text)))

        # Truncate to maximum 2 * k messages (k turns)
        if len(self.chat_history) > self.k * 2:
            self.chat_history = self.chat_history[-(self.k * 2):]

    def load_memory_variables(self, inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.return_messages:
            return {self.memory_key: list(self.chat_history)}
        # String representation
        lines = []
        for m in self.chat_history:
            role = "Human" if m.role == "user" else "AI" if m.role == "assistant" else m.role.title()
            lines.append(f"{role}: {m.content}")
        return {self.memory_key: "\n".join(lines)}

    def clear(self) -> None:
        self.chat_history.clear()