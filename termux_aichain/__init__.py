"""
==============================================================================
termux-aichain: Sovereign Zero-Dependency Edge AI Framework for Termux & Android
==============================================================================
Copyright (c) 2026 AMEVA Open-Source Foundation & UnoKim.
Licensed under the Apache License, Version 2.0.
"""

__version__ = "1.0.2"
__author__ = "UnoKim <uno-km@users.noreply.github.com>"

from termux_aichain.core.schema import (
    Message,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    UsageInfo,
    GenerationResult,
    StreamChunk,
)
from termux_aichain.core.prompt import (
    PromptTemplate,
    ChatPromptTemplate,
)
from termux_aichain.core.base import (
    Runnable,
    RunnableLambda,
    RunnableSequence,
    BaseChatModel,
)
from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat
from termux_aichain.core.providers.bitnet import BitNetChat
from termux_aichain.core.providers.local_server import (
    LocalServerConfig,
    LocalServerManager,
    LlamaCppServer,
    BitNetServer,
)
from termux_aichain.core.parsers import (
    StringOutputParser,
    JsonOutputParser,
    RegexOutputParser,
)
from termux_aichain.core.splitters import (
    Document,
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
    TextLoader,
    MarkdownLoader,
    JSONLoader,
)
from termux_aichain.graph.state import (
    StateGraph,
    CompiledGraph,
    START,
    END,
)
from termux_aichain.graph.agent import (
    Tool,
    tool,
    create_react_agent,
)
from termux_aichain.memory.buffer import ConversationBufferMemory
from termux_aichain.memory.sqlite import SQLiteEntityMemory, SQLiteVectorStore
from termux_aichain.memory.extractor import FactExtractor
from termux_aichain.serve.server import AgentServer, serve
from termux_aichain.serve.dashboard import DASHBOARD_HTML
from termux_aichain.trace.tracer import TraceSpan, Tracer, traceable
from termux_aichain.device.tools import (
    get_battery_status,
    get_sensor_data,
    get_device_location,
    record_speech_to_text,
    vibrate_device,
    send_notification,
    speak_tts,
    execute_shell,
    get_default_device_tools,
)
from termux_aichain.device.ecosystem import (
    transcribe_speech,
    generate_diffusion_image,
    browse_web_headless,
    get_ecosystem_tools,
)

__all__ = [
    "__version__",
    "Message",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "ToolMessage",
    "UsageInfo",
    "GenerationResult",
    "StreamChunk",
    "PromptTemplate",
    "ChatPromptTemplate",
    "Runnable",
    "RunnableLambda",
    "RunnableSequence",
    "BaseChatModel",
    "OpenAICompatibleChat",
    "BitNetChat",
    "LocalServerConfig",
    "LocalServerManager",
    "LlamaCppServer",
    "BitNetServer",
    "StringOutputParser",
    "JsonOutputParser",
    "RegexOutputParser",
    "Document",
    "CharacterTextSplitter",
    "RecursiveCharacterTextSplitter",
    "TextLoader",
    "MarkdownLoader",
    "JSONLoader",
    "StateGraph",
    "CompiledGraph",
    "START",
    "END",
    "Tool",
    "tool",
    "create_react_agent",
    "ConversationBufferMemory",
    "SQLiteEntityMemory",
    "SQLiteVectorStore",
    "FactExtractor",
    "AgentServer",
    "serve",
    "DASHBOARD_HTML",
    "TraceSpan",
    "Tracer",
    "traceable",
    "get_battery_status",
    "get_sensor_data",
    "get_device_location",
    "record_speech_to_text",
    "vibrate_device",
    "send_notification",
    "speak_tts",
    "execute_shell",
    "get_default_device_tools",
    "transcribe_speech",
    "generate_diffusion_image",
    "browse_web_headless",
    "get_ecosystem_tools",
]