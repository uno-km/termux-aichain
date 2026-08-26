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

Existing enterprise frameworks (LangChain, LlamaIndex, CrewAI, LangGraph) introduce heavy dependency graphs (`pydantic`, `aiohttp`, `sqlalchemy`, `tenacity`) and substantial memory overheads (200MB+ Base RSS). On Android/Termux devices with Low Memory Killers (LMK) and ARM architectures, these cause high cold-start latencies, wheel compilation failures, and OOM crashes.

`termux-aichain` is engineered under the **Zero-Heavy-Dependency** doctrine:
- **Python**: 100% Pure Standard Library (`urllib`, `asyncio`, `json`, `dataclasses`, `re`, `sqlite3`). No third-party wheels required.
- **Node.js / TypeScript**: Pure Standard ESM (`fetch`, `ReadableStream`, `events`). Zero external dependencies.
- **Native Edge Inference**: Direct SSE/REST interface for `llama-server`, `bitnet.cpp` (1-bit LLMs), `ollama`, `exo`, and OpenAI-compatible daemons.
- **Stateful Multi-Agent Graph**: Cyclic state machine and autonomous ReAct agent loops without LangGraph overhead.
- **Android Device Native**: Direct tool-calling integration with `termux-api` (battery, sensors, camera, GPS, TTS, STT).

---

## 🗺️ 6-Phase Engineering Roadmap

| Phase | Module | Scope & LangChain Equivalent | Status |
| :---: | :--- | :--- | :---: |
| **Phase 1** | **Core Engine** | Prompt templates, OpenAI/BitNet/llama-server adapters, `\|` Pipe chains, Parsers, Splitters | ✅ **Complete** |
| **Phase 2** | **Graph Engine** | LangGraph alternative: Stateful Multi-Agent loops, cyclic flows, conditional branches | ✅ **Complete** |
| **Phase 3** | **Memory Engine** | LangMem alternative: SQLite + Cosine similarity persistent edge long-term memory | ⏳ Next |
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
    base_url="http://127.0.0.1:8080/v1",
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

### 3. Stateful Cyclic Graph (LangGraph Alternative)

```python
from termux_aichain import StateGraph, START, END

workflow = StateGraph()

def think_step(state):
    return {"thought_count": state.get("thought_count", 0) + 1}

def decide_step(state):
    if state["thought_count"] >= 3:
        return END
    return "think"

workflow.add_node("think", think_step)
workflow.set_entry_point("think")
workflow.add_conditional_edges("think", decide_step)

app = workflow.compile()
final_state = app.invoke({"thought_count": 0})
print("Final State:", final_state)
```

### 4. Autonomous ReAct Agent with Tool Calling

```python
from termux_aichain import OpenAICompatibleChat, tool, create_react_agent, HumanMessage

@tool(name="check_battery", description="Checks current device battery level")
def check_battery() -> str:
    return "Battery level is 84%, status: Discharging"

llm = OpenAICompatibleChat(base_url="http://127.0.0.1:8080/v1")
agent = create_react_agent(model=llm, tools=[check_battery])

state = agent.invoke({"messages": [HumanMessage(content="Is the battery healthy?")]})
print("Agent Response:", state["messages"][-1].content)
```

---

## ⚡ Quick Start (Node.js / TypeScript)

```javascript
import { StateGraph, START, END } from "@termux-ai/chain";

const workflow = new StateGraph();
workflow.addNode("step1", (s) => ({ counter: (s.counter || 0) + 1 }));
workflow.setEntryPoint("step1");
workflow.addConditionalEdges("step1", (s) => (s.counter >= 5 ? END : "step1"));

const app = workflow.compile();
const res = await app.invoke({ counter: 0 });
console.log("Graph Execution Result:", res);
```

---

## 📊 Benchmark & Footprint Comparison

| Metric | LangChain + LangGraph (Server) | `termux-aichain` (Phase 1 & 2) |
| :--- | :---: | :---: |
| **External Dependencies** | 60+ packages | **0 (Zero)** |
| **Package Disk Size** | ~240 MB | **< 200 KB** |
| **Cold-Start Import Time** | ~1,800 ms | **< 15 ms** |
| **Base Memory Footprint (RSS)** | ~210 MB | **< 9 MB** |
| **Termux aarch64 Compatibility** | Wheel build errors | **100% Native Pure Python & Node** |

---

## 🧪 Testing

```bash
# Run Python Unit Tests (24 tests)
pytest tests -v

# Run Node.js Native Tests (6 tests)
node --test tests/*.test.js
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).  
Copyright (c) 2026 UnoKim & AMEVA Open-Source Foundation.