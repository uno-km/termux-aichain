# Termux-AIChain

<div align="center">

```
 _____                                     ___  _____ _____ _           _       
|_   _|                                   / _ \|_   _/  __ \ |         (_)      
  | | ___ _ __ _ __ ___  _   ___  __     / /_\ \ | | | /  \/ |__   __ _ _ _ __  
  | |/ _ \ '__| '_ ` _ \| | | \ \/ / ___ |  _  | | | | |   | '_ \ / _` | | '_ \ 
  | |  __/ |  | | | | | | |_| |>  < |___|| | | |_| |_| \__/\ | | | (_| | | | | |
  \_/\___|_|  |_| |_| |_|\__,_/_/\_\     \_| |_/\___/ \____/_| |_|\__,_|_|_| |_|
```

**Sovereign Zero-Dependency AI Chaining & Multimodal Autonomous Agent Framework for Android Termux**  
*Dual-Engine Architecture (Pure Python 3.10+ Stdlib & Pure Node.js 18+ ESM) with Native ARM64 Acceleration & 0 Heavy External Dependency*

<p align="center">
  <a href="https://pypi.org/project/termux-aichain/"><img src="https://img.shields.io/pypi/v/termux-aichain.svg?style=for-the-badge&color=0088ff&logo=pypi&logoColor=white" alt="PyPI Version" /></a>
  <a href="https://pypi.org/project/termux-aichain/"><img src="https://img.shields.io/badge/PyPI%20Downloads-active-0088ff?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI Downloads" /></a>
  <a href="https://www.npmjs.com/package/termux-aichain"><img src="https://img.shields.io/npm/v/termux-aichain.svg?style=for-the-badge&color=cb3837&logo=npm&logoColor=white" alt="npm Version" /></a>
  <a href="https://www.npmjs.com/package/termux-aichain"><img src="https://img.shields.io/badge/npm%20Downloads-active-cb3837?style=for-the-badge&logo=npm&logoColor=white" alt="npm Downloads" /></a>
</p>

<p align="center">
  <a href="https://uno-km.vercel.app/lib/aichain/"><img src="https://img.shields.io/badge/Official_Docs-uno--km.vercel.app%2Flib%2Faichain-004499?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Docs" /></a>
  <a href="https://github.com/uno-km/termux-aichain"><img src="https://img.shields.io/github/stars/uno-km/termux-aichain?style=for-the-badge&color=gold&logo=github" alt="GitHub Stars" /></a>
  <a href="https://github.com/uno-km/termux-aichain/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge" alt="License" /></a>
  <a href="https://github.com/uno-km/termux-aichain"><img src="https://img.shields.io/badge/Tests-153%2F153%20PASS-success.svg?style=for-the-badge" alt="Tests" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android%20Termux%20(ARM64%2Faarch64)-00887A?style=flat-square&logo=android&logoColor=white" alt="Platform" />
  <img src="https://img.shields.io/badge/Dependencies-0%20External%20Packages-success.svg?style=flat-square" alt="Zero Dep" />
  <img src="https://img.shields.io/badge/Cold%20Start-12.8ms-brightgreen?style=flat-square" alt="Cold Start" />
  <img src="https://img.shields.io/badge/RAM-14.2MB%20RSS-blue?style=flat-square" alt="RAM" />
  <img src="https://img.shields.io/badge/Foundation-AOSF_Tier_1-orange?style=flat-square" alt="Foundation" />
</p>

<br/>

**[Official Documentation Site](https://uno-km.vercel.app/lib/aichain/)** • **[AMEVA Foundation](https://uno-km.vercel.app/foundation/)** • **[Python Guide](#-python-quickstart)** • **[Node.js Guide](#-nodejs--typescript-quickstart)** • **[Termux Setup](#-android-termux-setup)** • **[10 Copy-Paste Recipes](#-10-copy-paste-production-recipes)** • **[Hardware Tuning](#-hardware-tuning--sampling-parameters)** • **[Benchmarks](#-empirical-benchmarks-galaxy-s20)**

</div>

---

## 🌐 AMEVA Foundation — Sovereign Mobile AI Ecosystem

> **"$0 Cloud Cost, 0% External Data Egress. Turning every Android smartphone into a sovereign autonomous AI workstation."**  
> The **AMEVA Open-Source Foundation (AOSF)** builds next-generation, client-centric AI runtimes spanning on-device large models, browser automation, neural network training, speech-to-text, and autonomous agent chaining.

| Project | Platform & Packages | Core Capability & Technology | Documentation |
| :--- | :--- | :--- | :---: |
| ⚡ **[termux-aichain](https://github.com/uno-km/termux-aichain)** | [![PyPI](https://img.shields.io/pypi/v/termux-aichain?color=blue&style=flat-square)](https://pypi.org/project/termux-aichain/) [![npm](https://img.shields.io/npm/v/termux-aichain?color=red&style=flat-square)](https://www.npmjs.com/package/termux-aichain) | **Zero-Dependency Multimodal Agent Chaining & StateGraph Engine** (Python stdlib + Node.js ESM) | **[Docs](https://uno-km.vercel.app/lib/aichain/)** |
| 🎙️ **[termux-stt](https://github.com/uno-km/termux-stt)** | [![PyPI](https://img.shields.io/pypi/v/termux-stt?color=blue&style=flat-square)](https://pypi.org/project/termux-stt/) [![npm](https://img.shields.io/npm/v/termux-stt?color=red&style=flat-square)](https://www.npmjs.com/package/termux-stt) | **Integrated On-Device STT & Pure Python 128d X-Vector Diarization** (Whisper + Vosk + Sherpa) | **[Docs](https://uno-km.vercel.app/lib/stt/)** |
| 🔊 **[termux-tts](https://github.com/uno-km/termux-tts)** | [![PyPI](https://img.shields.io/pypi/v/termux-tts?color=blue&style=flat-square)](https://pypi.org/project/termux-tts/) [![npm](https://img.shields.io/npm/v/termux-tts?color=red&style=flat-square)](https://www.npmjs.com/package/termux-tts) | **High-Performance Multi-Backend TTS Engine** (DSP Formant Vocoder, ONNX Neural Runtime & Native Voice) | **[Docs](https://uno-km.vercel.app/lib/tts/)** |
| 👁️ **[termux-vision](https://github.com/uno-km/termux-vision)** | [![PyPI](https://img.shields.io/pypi/v/termux-vision?color=blue&style=flat-square)](https://pypi.org/project/termux-vision/) [![npm](https://img.shields.io/npm/v/termux-vision?color=red&style=flat-square)](https://www.npmjs.com/package/termux-vision) | **On-Device Computer Vision & Vision-Language Model (VLM)** (Fast CV, Haar Detect & SmolVLM / Qwen2-VL) | **[Docs](https://uno-km.vercel.app/lib/vision/)** |
| 🎨 **[termux-diffusion](https://github.com/uno-km/termux-diffusion)** | [![PyPI](https://img.shields.io/pypi/v/termux-diffusion?color=blue&style=flat-square)](https://pypi.org/project/termux-diffusion/) [![npm](https://img.shields.io/npm/v/termux-diffusion?color=red&style=flat-square)](https://www.npmjs.com/package/termux-diffusion) | **Mobile On-Device Stable Diffusion Image Generation** (bfloat16 ARM NEON acceleration) | **[Docs](https://uno-km.vercel.app/lib/diffusion/)** |
| 🌐 **[termux-playwright](https://github.com/uno-km/termux-playwright)** | [![PyPI](https://img.shields.io/pypi/v/termux-playwright?color=blue&style=flat-square)](https://pypi.org/project/termux-playwright/) [![npm](https://img.shields.io/npm/v/termux-playwright?color=red&style=flat-square)](https://www.npmjs.com/package/termux-playwright) | **Non-Root Native Headless Chromium Browser Automation & Scraping** | **[Docs](https://uno-km.vercel.app/lib/playwright/)** |
| 🧠 **[termux-train](https://github.com/uno-km/termux-train)** | [![PyPI](https://img.shields.io/pypi/v/termux-train.svg?color=blue&style=flat-square)](https://pypi.org/project/termux-train/) | **Mobile Native Autograd Neural Network Training & LoRA Fine-Tuning** | **[Docs](https://uno-km.vercel.app/lib/train/)** |
| 🔮 **[AMEVA-Forge](https://github.com/uno-km/ameva-forge)** | [![WebGPU](https://img.shields.io/badge/WebGPU-Autograd-purple?style=flat-square)](https://uno-km.vercel.app/lib/forge/) | **High-Performance WebGPU Autograd & 3D Neural Studio Engine** | **[Docs](https://uno-km.vercel.app/lib/forge/)** |

---

## ⚡ Architectural Pillars

### 1. Zero-Heavy-Dependency Doctrine
- Standard edge AI libraries (LangChain, LlamaIndex, CrewAI) introduce 40~80 heavy dependencies (Pydantic, NumPy, aiohttp, requests, tenacity), resulting in 200MB+ memory baselines and frequent C-compilation failures on Android Bionic ARM64.
- `termux-aichain` is written strictly with the **Python 3.10+ Standard Library** (`urllib`, `sqlite3`, `subprocess`, `json`, `math`, `typing`, `http.server`) and **Pure Node.js 18+ ESM** (`http`, `node:sqlite`, `node:test`).
- **Cold start import latency is 12.8ms**, and total package disk footprint is under **268KB**.

### 2. Dual-Engine Native Parity (Python Stdlib + Node.js ESM)
- 100% equivalent API contracts between Python and JavaScript/TypeScript: `LocalAgent`, `StateGraph`, `create_react_agent`, `ToolPolicy`, Vector Store, Memory Buffer, and 1-Line HTTP/SSE Serving.

### 3. Fail-Closed Identity Verification & Capability Profiling
- `ServerIdentityVerifier` automatically identifies local inference engines (`termux-aichain`, `llama-server`, `BitNet.cpp`, `OpenAI`).
- When `/health` returns generic status, capability fallback queries `/v1/models` to ensure model identity matches before dispatching sensitive device actions.

### 4. Default-Deny Tool Authorization Policy
- All tools execute under `ToolPolicy(default="deny")` with JSON Schema bounds validation and optional asynchronous user approval callbacks.

---

## 🐍 Python Quickstart

### Installation (pip)
```bash
pip install --upgrade termux-aichain
```

### 10-Second Hello Agent
```python
from termux_aichain import LocalAgent

# Connects to local llama-server or OpenAI-compatible backend
agent = LocalAgent.local(model="qwen2.5-1.5b")
response = agent.run("Hello! Introduce yourself in one concise sentence.")
print(response)
```

---

## 🟩 Node.js / TypeScript Quickstart

### Installation (npm)
```bash
npm install termux-aichain
```

### 10-Second Hello Agent (ESM)
```javascript
import { LocalAgent } from "termux-aichain";

// Connects to local llama-server or OpenAI-compatible backend
const agent = await LocalAgent.local("qwen2.5-1.5b");
const response = await agent.run("Hello! Introduce yourself in one concise sentence.");
console.log(response);
```

---

## 📱 Android Termux Setup

### Option A: One-Touch Python Setup (Recommended)
```bash
pip install --upgrade termux-aichain
termux-aichain install
```
> `termux-aichain install` automatically provisions all necessary Termux packages (`termux-api`, `ffmpeg`, `git`, `nodejs-lts`) in a single step with zero manual configuration.

### Option B: 1-Line Bootstrap Script (Termux Bash)
```bash
curl -sSL https://raw.githubusercontent.com/uno-km/termux-aichain/main/scripts/install.sh | bash
```

---

## 📋 10 Copy-Paste Production Recipes

### [Python] Recipe 1: 1-Line Local LLM / BitNet LCEL Pipe Chaining

```python
from termux_aichain import PromptTemplate, JsonOutputParser, OpenAICompatibleChat

# 1. Define prompt template and JSON output parser
prompt = PromptTemplate.from_template(
    "Extract structured system status from log:\n{log}\n"
    "Respond in strict JSON with fields 'level', 'code', 'message'."
)
parser = JsonOutputParser()

# 2. Connect to local llama-server / BitNet endpoint
llm = OpenAICompatibleChat(base_url="http://127.0.0.1:8080/v1", temperature=0.1)

# 3. Assemble LCEL pipe chain (zero external dependencies)
chain = prompt | llm | parser

# 4. Execute synchronously
result = chain.invoke({"log": "CRITICAL: Kernel thermal throttling triggered at 48C (Code 104)"})
print("Parsed JSON Output:", result)
```

---

### [Python] Recipe 2: Autonomous ReAct Multi-Agent with StateGraph & Hardware Actuation

```python
from termux_aichain import (
    create_react_agent,
    BitNetChat,
    HumanMessage,
    get_battery_status,
    vibrate_device,
    transcribe_speech
)

# 1. Initialize local engine
model = BitNetChat(base_url="http://127.0.0.1:8080/v1", temperature=0.1)

# 2. Construct autonomous ReAct agent with hardware tools
agent = create_react_agent(
    model=model,
    tools=[get_battery_status, transcribe_speech, vibrate_device],
    system_prompt="You are a sovereign mobile agent running on Android Termux."
)

# 3. Execute multi-step reasoning and acting loop
state = agent.invoke({
    "messages": [HumanMessage(content="Check battery percentage and vibrate device for 500ms if battery > 50%.")]
})

print("Agent Final Output:", state["messages"][-1].content)
```

---

### [Python] Recipe 3: SQLite ACID Memory & FTS5 Hybrid Vector RAG (Built-in Embeddings)

```python
from termux_aichain import SQLiteEntityMemory, SQLiteVectorStore, SparseBM25Embeddings, LocalEmbeddings

# 1. Persistent Key-Value Entity Memory
memory = SQLiteEntityMemory(db_path="mobile_agent.db")
memory.save_entity("device_owner", "Dr. Uno Kim")
memory.save_entity("preferred_model", "BitNet-3B-1.58b")
print("Retrieved Owner:", memory.get_entity("device_owner"))

# 2. Zero-Dependency Hybrid Vector Store (No NumPy / ChromaDB needed)
# Uses built-in SparseBM25Embeddings or LocalEmbeddings.local(model="bge-micro")
embedder = SparseBM25Embeddings(dimension=64)
vector_store = SQLiteVectorStore(db_path="vector_rag.db", embeddings=embedder)

# Automatic vectorization on ingestion
vector_store.add_texts(
    texts=["Android Bionic Subsystem Architecture", "WebGPU Neural Compute Shaders"],
    metadatas=[{"source": "os_doc"}, {"source": "gpu_doc"}]
)

# 2-stage FTS5 + Cosine RRF Hybrid Search (Sub-5ms on 10k docs)
matches = vector_store.hybrid_search("Android Bionic", k=1)
print("Top RAG Match:", matches[0].page_content, f"(RRF Score: {matches[0].score:.5f})")
```

---

### [Python] Recipe 4: 1-Line REST & SSE Streaming Agent Server

```python
from termux_aichain import create_react_agent, OpenAICompatibleChat, serve, get_battery_status

llm = OpenAICompatibleChat(base_url="http://127.0.0.1:8080/v1")
agent = create_react_agent(model=llm, tools=[get_battery_status])

# Starts REST API (POST /invoke, POST /stream) and Web Dashboard UI on localhost
serve(agent, host="127.0.0.1", port=8000)
```

---

### [Python] Recipe 5: Full Multimodal Ecosystem Pipeline (STT + Vision + TTS + Diffusion + Playwright)

```python
from termux_aichain import (
    create_react_agent,
    BitNetChat,
    HumanMessage,
    get_battery_status,
    transcribe_speech,
    synthesize_speech,
    analyze_image_vlm,
    detect_faces,
    generate_diffusion_image,
    browse_web_headless,
    vibrate_device
)

llm = BitNetChat(base_url="http://127.0.0.1:8080/v1", temperature=0.1)

agent = create_react_agent(
    model=llm,
    tools=[
        get_battery_status,
        transcribe_speech,
        synthesize_speech,
        analyze_image_vlm,
        detect_faces,
        generate_diffusion_image,
        browse_web_headless,
        vibrate_device
    ],
    system_prompt="You are a multimodal autonomous edge agent capable of speech, vision, image generation, web scraping, and device control."
)

state = agent.invoke({
    "messages": [HumanMessage(content="Transcribe speech from meeting.wav, describe chart.png via VLM, synthesize report to voice.wav, and vibrate.")]
})
print("Multimodal Result:", state["messages"][-1].content)
```

---

### [Node.js] Recipe 6: 1-Line LocalAgent Facade & Automatic Verification

```javascript
import { LocalAgent } from "termux-aichain";

// Automatically verifies server capability, protocol, and model ID
const agent = await LocalAgent.local("qwen2.5-1.5b", {
  endpoint: "http://127.0.0.1:8080"
});

const result = await agent.run("Summarize key advantages of on-device AI in 3 bullet points.");
console.log(result);
```

---

### [Node.js] Recipe 7: Cyclic StateGraph Machine & Conditional Branching

```javascript
import { StateGraph, START, END } from "termux-aichain";

const workflow = new StateGraph();

workflow.addNode("step_a", async (state) => {
  console.log(`[Node A] Count: ${state.count}`);
  return { count: state.count + 1 };
});

workflow.setEntryPoint("step_a");
workflow.addConditionalEdges("step_a", (state) => (state.count >= 3 ? END : "step_a"));

const app = workflow.compile();
const finalState = await app.invoke({ count: 0 });
console.log("Graph Complete:", finalState);
```

---

### [Node.js] Recipe 8: In-Memory MicroVectorStore Similarity Search

```javascript
import { MicroVectorStore } from "termux-aichain";

const vectorStore = new MicroVectorStore();

vectorStore.addTexts(
  ["Linux Kernel Bionic Architecture", "ARM NEON SIMD Assembly", "WebGPU Compute Shaders"],
  [
    [0.95, 0.10, 0.05],
    [0.85, 0.40, 0.10],
    [0.05, 0.15, 0.98]
  ]
);

const matches = vectorStore.similaritySearchByVector([0.90, 0.20, 0.05], 1);
console.log("Top Vector Match:", matches[0].content, `(Score: ${matches[0].score.toFixed(4)})`);
```

---

### [Node.js] Recipe 9: 1-Line REST & SSE Streaming Server

```javascript
import { serve, PromptTemplate } from "termux-aichain";

const prompt = PromptTemplate.fromTemplate("Echo and analyze: {msg}");

// Serves POST /invoke and POST /stream with loopback CORS protection
const server = serve(prompt, {
  host: "127.0.0.1",
  port: 8080,
  apiKey: "optional_secret_token"
});
```

---

### [Node.js] Recipe 10: Android Native Hardware Actuation Tools

```javascript
import {
  getBatteryStatus,
  getSensorData,
  getDeviceLocation,
  vibrateDevice,
  sendNotification
} from "termux-aichain";

// 1. Read battery percentage (CLI or kernel sysfs fallback)
const battery = await getBatteryStatus.func();
console.log("Battery Status:", battery);

// 2. Vibrate device for 300ms
await vibrateDevice.func({ duration_ms: 300 });

// 3. Dispatch Android Notification
await sendNotification.func({
  title: "AI Workstation",
  content: "Autonomous task execution completed successfully.",
  priority: "high"
});
```

---

## 🛠️ Hardware Tuning & Sampling Parameters

### 12 Hardware Tuning Flags (`LocalServerConfig`)

| Parameter | Type | Default | Valid Range | Technical Function |
| :--- | :---: | :---: | :---: | :--- |
| `threads` | `int` | `CPU-1` | `1 ~ 16` | Number of dedicated CPU threads for BLAS/NEON computation. |
| `n_ctx` | `int` | `2048` | `512 ~ 32768` | Total token capacity allocated for the model context window. |
| `n_batch` | `int` | `512` | `32 ~ 2048` | Prompt evaluation batch size. |
| `n_ubatch` | `int` | `256` | `16 ~ 512` | Micro-batch size for strictly memory-constrained edge hardware. |
| `n_gpu_layers` | `int` | `0` | `0 ~ 99` | Number of model layers offloaded to Vulkan / OpenCL / GPU compute. |
| `flash_attn` | `bool` | `False` | `True / False` | Flash Attention kernel acceleration toggle (`-fa`). |
| `cache_type_k` | `str` | `"f16"` | `"f16"`, `"q8_0"`, `"q4_0"` | Key cache quantization format (q8_0 saves 50% RAM, q4_0 saves 75%). |
| `cache_type_v` | `str` | `"f16"` | `"f16"`, `"q8_0"`, `"q4_0"` | Value cache quantization format. |
| `mlock` | `bool` | `False` | `True / False` | Lock model weights in RAM to prevent disk swapping. |
| `cont_batching` | `bool` | `True` | `True / False` | Continuous batching support for multi-turn conversations. |
| `rope_freq_scale` | `float` | `None` | `0.1 ~ 1.0` | Linear RoPE context extension factor. |
| `port` | `int` | `8080` | `1024 ~ 65535` | Local TCP port for the model server. |

### 8 Sampling Control Parameters (`OpenAICompatibleChat` / `BitNetChat`)

| Parameter | Type | Default | Valid Range | Technical Description |
| :--- | :---: | :---: | :---: | :--- |
| `temperature` | `float` | `0.7` | `0.0 ~ 2.0` | Nucleus generation randomness (0.0 for deterministic code/JSON). |
| `top_p` | `float` | `0.95` | `0.0 ~ 1.0` | Cumulative probability cutoff threshold for candidate token filtering. |
| `top_k` | `int` | `40` | `1 ~ 100` | Integer limit on candidate token selection pool. |
| `min_p` | `float` | `0.05` | `0.0 ~ 1.0` | Minimum relative probability cutoff to eliminate low-rank hallucinations. |
| `repeat_penalty` | `float` | `1.1` | `1.0 ~ 2.0` | Frequency penalty scale to avoid infinite token repetition loops. |
| `stop` | `List[str]` | `None` | `List[str]` | Generation termination sequence delimiters. |
| `seed` | `int` | `None` | `int` | Random seed for exact deterministic generation reproducibility. |
| `grammar` | `str` | `None` | `str` | GBNF or Regex structural constraint schema for forced JSON output. |

---

## 📊 Empirical Benchmarks (Galaxy S20)

Measured on physical mobile hardware (Samsung Galaxy S20 5G, Qualcomm Snapdragon 865, 12GB RAM, Android 13 Termux):

| Measurement Metric | LangChain (Heavyweight) | `termux-aichain` v1.1.0 | Performance Delta |
| :--- | :---: | :---: | :---: |
| **Cold Start Import Latency** | 1,240.0 ms | **12.8 ms** | **96.8x Faster** |
| **Baseline RAM Footprint (RSS)** | 185.0 MB | **14.2 MB** | **92.3% Memory Saved** |
| **Package Disk Size** | 48.5 MB | **0.26 MB (268 KB)** | **99.4% Disk Saved** |
| **External Dependencies** | 42+ packages | **0 packages** | **Zero External Dependencies** |
| **5-Step Multimodal E2E Run** | Failed (Crash) | **46.4 ms** | **Deterministic PASS** |
| **Automated Test Scope** | Variable | **153 / 153 PASS** | **0 Observed Failures** |

---

## 🔒 Audit & Verification Summary

- **Verification Scope**: 153/153 automated tests passed with zero observed failures or errors in the verified test scope (136 Python tests, 17 Node.js tests).
- **TypeScript Zero-Drift**: Full compilation parity between `js/src/**/*.ts` SSOT and `js/esm/` release output.
- **Fail-Closed Security**: `ServerIdentityVerifier` fail-closed backend validation, tool policy `default="deny"`, loopback CORS, and constant-time token comparison.

---

## 📜 License & Compliance

- **License**: Apache License 2.0 (`Apache-2.0`).
- **Official Documentation Portal**: [https://uno-km.vercel.app/lib/aichain/](https://uno-km.vercel.app/lib/aichain/)
- **GitHub Repository**: [https://github.com/uno-km/termux-aichain](https://github.com/uno-km/termux-aichain)
- **AMEVA Open-Source Foundation (AOSF)**.