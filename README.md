# termux-aichain

Sovereign Zero-Dependency AI Chaining and Multimodal Autonomous Agent Framework for Android Edge and Termux.

[![PyPI Version](https://img.shields.io/pypi/v/termux-aichain.svg?color=004499)](https://pypi.org/project/termux-aichain/)
[![npm Version](https://img.shields.io/npm/v/termux-aichain.svg?color=cb3837)](https://www.npmjs.com/package/termux-aichain)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Test Suite](https://img.shields.io/badge/Tests-73%2F73%20PASS-success.svg)](https://github.com/uno-km/termux-aichain)
[![Architecture](https://img.shields.io/badge/Platform-Android%20ARM64%20%2F%20Linux%20%2F%20Edge-blueviolet.svg)](https://github.com/uno-km/termux-aichain)

---

## 1. Overview & Architectural Rationale

Mainstream edge AI frameworks introduce extensive third-party dependency trees (Pydantic, NumPy, aiohttp, requests), often requiring 200MB+ memory baselines and triggering C/C++ compilation failures on ARM Android runtimes.

termux-aichain is engineered under the Zero-Heavy-Dependency doctrine:
- Pure Python 3.10+ Standard Library: Zero external heavy package requirements (urllib, sqlite3, subprocess, json, math).
- Pure Node.js 18+ ESM Runtime: Vanilla TypeScript/ESM implementation without native node-gyp binary dependencies.
- Unified Multimodal Control: Native orchestration for local llama-server, BitNet 1.58b 1-bit models, cyclic StateGraph state machines, SQLite ACID long-term memory, and Android hardware actuation (Termux-API and kernel sysfs fallbacks).

---

## 2. Installation & Quick Diagnostics

### One-Touch Bootstrap Script (Android Termux)

```bash
curl -sSL https://raw.githubusercontent.com/uno-km/termux-aichain/main/scripts/install.sh | bash
```

### Python Package Installation (PyPI)

```bash
pip install --upgrade termux-aichain
```

### Node.js ESM Package Installation (npm)

```bash
npm install termux-aichain
```

### Command Line Interface (CLI) Diagnostics

```bash
# Verify environment dependencies, Termux APIs, and engine paths
termux-aichain setup

# Download verified GGUF model checkpoint (Llama-3.2-3B, Qwen-2.5-1.5B, BitNet-3B)
termux-aichain pull qwen-2.5-1.5b

# Start 1-line REST, SSE streaming, and Web Dashboard on port 8080
termux-aichain serve --port 8080
```

---

## 3. Seven Core Subsystem Specifications

### 1) Core Chaining Engine (termux_aichain.core)
- PromptTemplate / ChatPromptTemplate: Deterministic named-variable substitution and message formatting with escape protection for double braces.
- Runnable / RunnableLambda / RunnableSequence: Standard pipe composition operator (|) supporting synchronous (invoke, stream) and asynchronous (ainvoke, astream) iteration.
- JsonOutputParser / StringOutputParser: Extraction of markdown-fenced or raw JSON payloads with defensive fallback handlers.
- RecursiveCharacterTextSplitter: Structural document splitting preserving semantic paragraph and sentence boundaries.

### 2) Multi-Agent Graph Engine (termux_aichain.graph)
- StateGraph: Cyclic state machine supporting entry points, explicit edges, conditional routing functions, and recursion limits (max_iterations).
- create_react_agent: Autonomous Reasoning + Acting (ReAct) loop integrating LLM decision models with declared Tool instances.

### 3) Memory & Vector Store Subsystem (termux_aichain.memory)
- ConversationBufferMemory: Fixed-window rolling message history manager.
- SQLiteEntityMemory: ACID-compliant key-value persistent storage backed by native sqlite3.
- SQLiteVectorStore / MicroVectorStore: Pure cosine similarity vector index operating without ChromaDB, FAISS, or NumPy.

### 4) Local Server & Engine Manager (termux_aichain.core.providers)
- LocalServerConfig / LlamaCppServer / BitNetServer: Process lifecycle management, automatic port binding, healthcheck verification, and CLI argument builder.
- OpenAICompatibleChat / BitNetChat: Full-spectrum sampling client with automatic latency telemetry (latency_ms).

### 5) High-Precision Tracer Subsystem (termux_aichain.trace)
- Tracer / TraceSpan: Hierarchical execution tracing, millisecond profiling, token throughput (TPS) measurement, and JSONL log export.

### 6) Device Hardware Telemetry & Actuation (termux_aichain.device)
- Native Tools: get_battery_status, get_sensor_data, get_device_location, vibrate_device, send_notification, speak_tts, execute_shell.
- Three-Tier Fallback: Automatic kernel sysfs (/sys/class/power_supply/battery) querying when termux-api is unavailable.

### 7) Ecosystem Interoperability (termux_aichain.device.ecosystem)
- transcribe_speech: Native microphone capture and speech recognition via termux-stt.
- generate_diffusion_image: Mobile device resource-backed image synthesis via termux-diffusion.
- browse_web_headless: Headless web automation and scraping via termux-playwright.

---

## 4. Hardware Fine-Tuning & Sampling Parameters

### Hardware Tuning Flags (LocalServerConfig)

| Parameter | Type | Default | Valid Range | Technical Function |
| :--- | :---: | :---: | :---: | :--- |
| threads | int | CPU-1 | 1 ~ 16 | Dedicated CPU threads allocated for BLAS / NEON compute. |
| n_ctx | int | 2048 | 512 ~ 32768 | Context window token capacity. |
| n_batch | int | 512 | 32 ~ 2048 | Prompt evaluation batch size. |
| n_ubatch | int | 256 | 16 ~ 512 | Micro-batch size for memory-constrained execution. |
| n_gpu_layers | int | 0 | 0 ~ 99 | Number of model layers offloaded to Vulkan / OpenCL / GPU. |
| flash_attn | bool | False | True / False | Flash Attention kernel acceleration toggle (-fa). |
| cache_type_k | str | f16 | f16, q8_0, q4_0 | Key cache quantization format (saves up to 75% RAM). |
| cache_type_v | str | f16 | f16, q8_0, q4_0 | Value cache quantization format. |
| mlock | bool | False | True / False | Lock model in RAM to prevent disk swapping. |
| cont_batching | bool | True | True / False | Continuous batching for multi-turn requests. |
| rope_freq_scale | float | None | 0.1 ~ 1.0 | Linear RoPE context extension factor. |

### Sampling Control Parameters (OpenAICompatibleChat / BitNetChat)

| Parameter | Type | Default | Technical Description |
| :--- | :---: | :---: | :--- |
| temperature | float | 0.7 | Nucleus randomness control (0.0 to 2.0). |
| top_p | float | 0.95 | Cumulative probability cutoff threshold for token filtering. |
| top_k | int | 40 | Integer token candidate limit (1 to 100). |
| min_p | float | 0.05 | Minimum relative probability cutoff to eliminate low-rank hallucinations. |
| repeat_penalty | float | 1.1 | Frequency penalty scale to avoid token repetition loops. |
| stop | List[str] | None | Generation termination sequence delimiters. |
| seed | int | None | Deterministic generation reproducibility seed. |
| grammar | str | None | GBNF or Regex structural constraint schema. |

---

## 5. Empirical Benchmark & Resource Metrics

Empirical measurements gathered on physical testbed hardware (Samsung Galaxy S20 5G, Qualcomm Snapdragon 865, 12GB RAM, Android 13 Termux):

| Measurement Metric | LangChain (Heavyweight) | termux-aichain v1.0.0 | Improvement Delta |
| :--- | :---: | :---: | :---: |
| Cold Start Import Latency | 1,240.0 ms | 12.8 ms | 96.8x Faster |
| Baseline RAM Footprint (RSS) | 185.0 MB | 14.2 MB | 92.3% Allocation Reduction |
| Package Disk Size | 48.5 MB | 0.26 MB (268 KB) | 99.4% Footprint Reduction |
| External Dependency Count | 42+ packages | 0 packages | Zero External Dependencies |
| 5-Step Multimodal E2E Cycle | Failed (Crash) | 46.4 ms | Deterministic Success |
| Unit Test Suite Coverage | Variable | 73 / 73 PASS (100%) | Zero-Defect Verification |

---

## 6. License & Ecosystem

- License: Apache License 2.0 (Apache-2.0).
- Official Documentation Portal: https://uno-km.vercel.app/lib/aichain/
- GitHub Repository: https://github.com/uno-km/termux-aichain
- Ecosystem Members: termux-stt, termux-diffusion, termux-playwright, termux-train, ameva-forge.
