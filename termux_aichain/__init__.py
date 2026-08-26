"""
==============================================================================
termux-aichain: Sovereign Zero-Dependency Edge AI Framework for Termux & Android
==============================================================================
Copyright (c) 2026 AMEVA Open-Source Foundation & UnoKim.
Licensed under the Apache License, Version 2.0.
"""

from __future__ import annotations
import importlib
from typing import Any

__version__ = "1.0.11"
__author__ = "UnoKim <uno-km@users.noreply.github.com>"

_LAZY_IMPORTS = {
    # Schema
    "Message": ("termux_aichain.core.schema", "Message"),
    "HumanMessage": ("termux_aichain.core.schema", "HumanMessage"),
    "AIMessage": ("termux_aichain.core.schema", "AIMessage"),
    "SystemMessage": ("termux_aichain.core.schema", "SystemMessage"),
    "ToolMessage": ("termux_aichain.core.schema", "ToolMessage"),
    "UsageInfo": ("termux_aichain.core.schema", "UsageInfo"),
    "GenerationResult": ("termux_aichain.core.schema", "GenerationResult"),
    "StreamChunk": ("termux_aichain.core.schema", "StreamChunk"),
    # Prompt
    "PromptTemplate": ("termux_aichain.core.prompt", "PromptTemplate"),
    "ChatPromptTemplate": ("termux_aichain.core.prompt", "ChatPromptTemplate"),
    # Base
    "Runnable": ("termux_aichain.core.base", "Runnable"),
    "RunnableLambda": ("termux_aichain.core.base", "RunnableLambda"),
    "RunnableSequence": ("termux_aichain.core.base", "RunnableSequence"),
    "BaseChatModel": ("termux_aichain.core.base", "BaseChatModel"),
    # Providers
    "OpenAICompatibleChat": ("termux_aichain.core.providers.openai_compatible", "OpenAICompatibleChat"),
    "BitNetChat": ("termux_aichain.core.providers.bitnet", "BitNetChat"),
    "LocalServerConfig": ("termux_aichain.core.providers.local_server", "LocalServerConfig"),
    "LocalServerManager": ("termux_aichain.core.providers.local_server", "LocalServerManager"),
    "LlamaCppServer": ("termux_aichain.core.providers.local_server", "LlamaCppServer"),
    "BitNetServer": ("termux_aichain.core.providers.local_server", "BitNetServer"),
    # Parsers
    "StringOutputParser": ("termux_aichain.core.parsers", "StringOutputParser"),
    "JsonOutputParser": ("termux_aichain.core.parsers", "JsonOutputParser"),
    "RegexOutputParser": ("termux_aichain.core.parsers", "RegexOutputParser"),
    # Splitters
    "Document": ("termux_aichain.core.splitters", "Document"),
    "CharacterTextSplitter": ("termux_aichain.core.splitters", "CharacterTextSplitter"),
    "RecursiveCharacterTextSplitter": ("termux_aichain.core.splitters", "RecursiveCharacterTextSplitter"),
    "TextLoader": ("termux_aichain.core.splitters", "TextLoader"),
    "MarkdownLoader": ("termux_aichain.core.splitters", "MarkdownLoader"),
    "JSONLoader": ("termux_aichain.core.splitters", "JSONLoader"),
    # Graph
    "StateGraph": ("termux_aichain.graph.state", "StateGraph"),
    "CompiledGraph": ("termux_aichain.graph.state", "CompiledGraph"),
    "START": ("termux_aichain.graph.state", "START"),
    "END": ("termux_aichain.graph.state", "END"),
    "Tool": ("termux_aichain.graph.agent", "Tool"),
    "tool": ("termux_aichain.graph.agent", "tool"),
    "create_react_agent": ("termux_aichain.graph.agent", "create_react_agent"),
    # Memory
    "ConversationBufferMemory": ("termux_aichain.memory.buffer", "ConversationBufferMemory"),
    "SQLiteEntityMemory": ("termux_aichain.memory.sqlite", "SQLiteEntityMemory"),
    "SQLiteVectorStore": ("termux_aichain.memory.sqlite", "SQLiteVectorStore"),
    "FactExtractor": ("termux_aichain.memory.extractor", "FactExtractor"),
    # Serve
    "AgentServer": ("termux_aichain.serve.server", "AgentServer"),
    "serve": ("termux_aichain.serve.server", "serve"),
    "DASHBOARD_HTML": ("termux_aichain.serve.dashboard", "DASHBOARD_HTML"),
    # Trace
    "TraceSpan": ("termux_aichain.trace.tracer", "TraceSpan"),
    "Tracer": ("termux_aichain.trace.tracer", "Tracer"),
    "traceable": ("termux_aichain.trace.tracer", "traceable"),
    # Device Tools
    "get_battery_status": ("termux_aichain.device.tools", "get_battery_status"),
    "get_sensor_data": ("termux_aichain.device.tools", "get_sensor_data"),
    "get_device_location": ("termux_aichain.device.tools", "get_device_location"),
    "record_speech_to_text": ("termux_aichain.device.tools", "record_speech_to_text"),
    "vibrate_device": ("termux_aichain.device.tools", "vibrate_device"),
    "send_notification": ("termux_aichain.device.tools", "send_notification"),
    "speak_tts": ("termux_aichain.device.tools", "speak_tts"),
    "execute_shell": ("termux_aichain.device.tools", "execute_shell"),
    "get_default_device_tools": ("termux_aichain.device.tools", "get_default_device_tools"),
    # Ecosystem Tools
    "infer_bitnet_llm": ("termux_aichain.device.ecosystem", "infer_bitnet_llm"),
    "transcribe_speech": ("termux_aichain.device.ecosystem", "transcribe_speech"),
    "generate_diffusion_image": ("termux_aichain.device.ecosystem", "generate_diffusion_image"),
    "browse_web_headless": ("termux_aichain.device.ecosystem", "browse_web_headless"),
    "get_ecosystem_tools": ("termux_aichain.device.ecosystem", "get_ecosystem_tools"),
}

__all__ = ["__version__"] + list(_LAZY_IMPORTS.keys())

def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        val = getattr(mod, attr_name)
        globals()[name] = val
        return val
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_IMPORTS.keys()))