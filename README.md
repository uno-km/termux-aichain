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

Existing enterprise frameworks (LangChain, LlamaIndex, CrewAI) introduce heavy dependency graphs (`pydantic`, `aiohttp`, `sqlalchemy`, `tenacity`) and substantial memory overheads (200MB+ Base RSS). On Android/Termux devices with Low Memory Killers (LMK) and ARM architectures, these cause high cold-start latencies, wheel compilation failures, and OOM crashes.

`termux-aichain` is engineered under the **Zero-Heavy-Dependency** doctrine:
- **Python**: 100% Pure Standard Library (`urllib`, `asyncio`, `json`, `dataclasses`, `re`, `sqlite3`). No third-party wheels required.
- **Node.js / TypeScript**: Pure Standard ESM (`fetch`, `ReadableStream`, `events`). Zero external dependencies.
- **Native Edge Inference**: Direct SSE/REST interface for `llama-server`, `bitnet.cpp` (1-bit LLMs), `ollama`, `exo`, and OpenAI-compatible daemons.
- **Android Device Native**: Direct tool-calling integration with `termux-api` (battery, sensors, camera, GPS, TTS, STT).

---

## 🗺️ 6-Phase Engineering Roadmap

| Phase | Module | Scope & LangChain Equivalent | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Core Engine** | Prompt templates, OpenAI/BitNet/llama-server adapters, `\|` Pipe chains, Parsers, Splitters | ✅ **Complete** |
| **Phase 2** | **Graph Engine** | LangGraph alternative: Stateful Multi-Agent loops, cyclic flows, conditional branches | ⏳ Next |
| **Phase 3** | **Memory Engine** | LangMem alternative: SQLite + Cosine similarity persistent edge long-term memory | ⏳ Planned |
| **Phase 4** | **Serve Engine** | LangServe alternative: 1-line local REST & SSE streaming server on Termux WiFi | ⏳ Planned |
| **Phase 5** | **Trace Engine** | LangSmith alternative: CLI tree logger, latency profiler, token counter & TPS meter | ⏳ Planned |
| **Phase 6** | **Device Toolkit** | Android hardware control: Battery, light sensor, gyro, camera, GPS, TTS, notifications | ⏳ Planned |

---

## 🚀 Quick Start (Python)

### 1. Installation

```bash
# In Termux or any Linux/macOS/Windows terminal:
git clone https://github.com/uno-km/termux-aichain.git
cd termux-aichain
pip install -e .
```

### 2. Basic Chaining Pipeline (`prompt | model | parser`)

```python
from termux_aichain import (
    ChatPromptTemplate,
    OpenAICompatibleChat,
    JsonOutputParser,
)

# 1. Connect to local llama-server or bitnet.cpp daemon
llm = OpenAICompatibleChat(
    base_url="http://127.0.0.1:8080/v1",  # Local llama-server or bitnet.cpp
    model="bitnet-b1.58-3b",
    temperature=0.2,
)

# 2. Define chat prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an on-device AI running on Termux ({device}). Always reply in valid JSON."),
    ("user", "Analyze battery health: level is {battery}%, status is {status}.")
])

# 3. Create pipeline using | operator
chain = prompt | llm | JsonOutputParser()

# 4. Invoke chain
result = chain.invoke({"device": "Galaxy S20", "battery": 85, "status": "Discharging"})
print("Parsed JSON Result:", result)
```

### 3. Real-time SSE Streaming

```python
from termux_aichain import OpenAICompatibleChat

llm = OpenAICompatibleChat(base_url="http://127.0.0.1:8080/v1")

for chunk in llm.stream("Explain 1-bit LLM architecture in 3 bullet points."):
    print(chunk.delta, end="", flush=True)
print(f"\n[Completed in {chunk.usage.latency_ms} ms]")
```

### 4. Edge Document Splitting & Chunking

```python
from termux_aichain import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=20)
docs = splitter.split_text("Termux AI Chain enables high performance on-device AI...")
for i, d in enumerate(docs):
    print(f"Chunk #{i}: {d}")
```

---

## ⚡ Quick Start (Node.js / TypeScript)

### 1. Pure ESM Usage

```javascript
import {
  ChatPromptTemplate,
  OpenAICompatibleChat,
  JsonOutputParser
} from "./dist/index.js";

const llm = new OpenAICompatibleChat({
  baseUrl: "http://127.0.0.1:8080/v1",
  model: "bitnet-b1.58-3b"
});

const prompt = ChatPromptTemplate.fromMessages([
  ["system", "You are an assistant running on Termux."],
  ["user", "Provide advice for battery level {battery}%."]
]);

const chain = prompt.pipe(llm).pipe(new JsonOutputParser());
const result = await chain.invoke({ battery: 42 });
console.log(result);
```

---

## 📊 Benchmark & Footprint Comparison

| Metric | LangChain (Server) | `termux-aichain` (Phase 1) |
| :--- | :---: | :---: |
| **External Dependencies** | 40+ packages | **0 (Zero)** |
| **Package Disk Size** | ~180 MB | **< 150 KB** |
| **Cold-Start Import Time** | ~1,200 ms | **< 12 ms** |
| **Base Memory Footprint (RSS)** | ~185 MB | **< 8 MB** |
| **Termux aarch64 Compatibility** | Wheel build errors | **100% Native Pure Python & Node** |

---

## 🧪 Testing

```bash
# Run Python Unit Tests (18 tests)
pytest tests -v

# Run Node.js Native Tests
node --test tests/core.test.js
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 UnoKim & AMEVA Open-Source Foundation.