"""
==============================================================================
termux-aichain Core Engine: BitNet.cpp 1-Bit LLM Provider Adapter
==============================================================================
Specialized zero-dependency provider for 1-bit and ternary quantized LLMs
(BitNet b1.58, Llama-3-BitNet) running via bitnet.cpp or llama.cpp on edge.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat

class BitNetChat(OpenAICompatibleChat):
    """Specialized lightweight chat provider for BitNet.cpp 1-bit quantized local engines."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        model: str = "bitnet-b1.58-3b",
        temperature: float = 0.1,
        max_tokens: int = 256,
        timeout: float = 60.0
    ):
        super().__init__(
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )