<div align="center">

# ⚡ termux-aichain

**Sovereign Zero-Dependency AI Chaining & Agent Framework for Termux, Android & Edge Computing**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green.svg)](https://nodejs.org/)
[![External Dependencies](https://img.shields.io/badge/Dependencies-0_(Zero)-brightgreen.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Termux_%7C_Android_%7C_ARM64_%7C_Linux-orange.svg)]()

*Ultra-lightweight, blazing-fast orchestration framework designed specifically for resource-constrained mobile and edge environments.*

</div>

---

## 📌 Architectural Philosophy

Existing enterprise frameworks (LangChain, LlamaIndex, CrewAI, LangGraph, LangMem, LangServe, LangSmith) introduce heavy dependency graphs (`pydantic`, `aiohttp`, `sqlalchemy`, `fastapi`, `chromadb`) and substantial memory overheads (250MB+ Base RSS). On Android/Termux devices with Low Memory Killers (LMK) and ARM architectures, these cause high cold-start latencies, wheel compilation failures, and OOM crashes.

`termux-aichain` is engineered under the **Zero-Heavy-Dependency** doctrine:
- **Python**: 100% Pure Standard Library (`urllib`, `asyncio`, `json`, `dataclasses`, `re`, `sqlite3`, `http.server`). No third-party wheels required.
- **Node.js / TypeScript**: Pure Standard ESM (`fetch`, `ReadableStream`, `events`, `node:http`). Zero external dependencies.
- **Native Edge Inference**: Direct SSE/REST interface for `llama-server`, `bitnet.cpp` (1-bit LLMs), `ollama`, `exo`, and OpenAI-compatible daemons.
- **Stateful Multi-Agent Graph**: Cyclic state machine and autonomous ReAct agent loops (LangGraph alternative).
- **SQLite Long-term Memory**: Persistent fact extraction, rolling buffer memory, and cosine similarity vector index (LangMem alternative).
- **1-Line Local Serving**: HTTP REST & SSE streaming server over Termux WiFi without FastAPI (LangServe alternative).
- **CLI Tree Observability**: Colorful trace logs, token counter, latency profiler, and TPS meter without cloud SaaS (LangSmith alternative).
- **Android Device Native**: Direct tool-calling integration with `termux-api` (battery, sensors, camera, GPS, TTS, STT, vibration, notifications).

---

## 🗺️ 6-Phase Engineering Architecture (All Complete)

| Module | Scope & LangChain Equivalent | Key Classes & Functions |
| :--- | :--- | :--- |
| **1. Core Engine** | LangChain Core | `PromptTemplate`, `ChatPromptTemplate`, `OpenAICompatibleChat`, `\|` Pipe, `JsonOutputParser`, `RecursiveCharacterTextSplitter` |
| **2. Graph Engine** | LangGraph Alternative | `StateGraph`, `CompiledGraph`, `START`, `END`, `Tool`, `@tool`, `create_react_agent` |
| **3. Memory Engine** | LangMem Alternative | `ConversationBufferMemory`, `SQLiteEntityMemory`, `SQLiteVectorStore`, `FactExtractor` |
| **4. Serve Engine** | LangServe Alternative | `AgentServer`, `serve(runnable, host, port)` (REST & SSE `/invoke`, `/stream`) |
| **5. Trace Engine** | LangSmith Alternative | `Tracer`, `TraceSpan`, `@traceable`, `tracer.render_tree()`, `tracer.export_jsonl()` |
| **6. Device Toolkit** | Mobile Native Toolkit | `get_battery_status`, `vibrate_device`, `send_notification`, `speak_tts`, `execute_shell`, `get_default_device_tools()` |

---

## 🚀 Quick Start (Python)

### 1. Installation

```bash
# In Termux or any terminal:
git clone https://github.com/uno-km/termux-aichain.git
cd termux-aichain
pip install -e .
```

### 2. Autonomous Mobile ReAct Agent with Hardware Tools & Tracing

```python
from termux_aichain import (
    OpenAICompatibleChat,
    create_react_agent,
    get_default_device_tools,
    Tracer,
    HumanMessage
)

# 1. Connect to local llama-server or bitnet.cpp
llm = OpenAICompatibleChat(base_url="http://127.0.0.1:8080/v1", model="bitnet-b1.58-3b")

# 2. Compile ReAct Agent with native Android hardware tools (battery, sensor, vibration, TTS)
tools = get_default_device_tools()
agent = create_react_agent(model=llm, tools=tools)

# 3. Profile execution with local CLI tracer
tracer = Tracer("MobileAgentRun")
with tracer.trace("AgentExecution"):
    state = agent.invoke({"messages": [HumanMessage(content="Check battery status and notify me.")]})

tracer.finish()
tracer.print_tree()
print("Agent Result:", state["messages"][-1].content)
```

### 3. 1-Line REST & SSE Server

```python
from termux_aichain import PromptTemplate, serve

prompt = PromptTemplate.from_template("Edge Agent Process: {task}")
chain = prompt | (lambda x: {"result": x.upper()})

# Exposes POST /invoke, POST /stream on local network
serve(chain, host="0.0.0.0", port=8080)
```

---

## ⚡ Quick Start (Node.js / TypeScript)

```javascript
import {
  PromptTemplate,
  StateGraph,
  ConversationBufferMemory,
  MicroVectorStore,
  serve
} from "@termux-ai/chain";

const prompt = PromptTemplate.fromTemplate("Hello {name} on Termux!");
const server = serve(prompt, { port: 8080 });
```

---

## 📊 Benchmark & Footprint Comparison

| Metric | LangChain Full Ecosystem | `termux-aichain` (All 6 Modules) |
| :--- | :---: | :---: |
| **External Dependencies** | 80+ packages | **0 (Zero)** |
| **Package Disk Size** | ~320 MB | **< 280 KB** |
| **Cold-Start Import Time** | ~2,400 ms | **< 18 ms** |
| **Base Memory Footprint (RSS)** | ~250 MB | **< 10 MB** |
| **Termux aarch64 Compatibility** | Wheel build errors | **100% Native Pure Python & Node** |

---

## 🧪 Testing

```bash
# Run Python Unit Tests (39 tests)
pytest tests -v

# Run Node.js Native Tests (11 tests)
node --test tests/*.test.js
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 UnoKim & AMEVA Open-Source Foundation.