# termux-aichain

> **Autonomous Multi-Agent Workflow Engine & Edge Chain Orchestrator for Android Termux**  
> *Dual-Engine Python & Node.js · Graph-State Workflow · Hardware Diagnostics · Local LLM Tool Binding*

---

## ⚡ 5-Minute Quickstart

### Python Installation

`ash
# In Android Termux:
pkg update && pkg install -y python python-numpy git
pip install termux-aichain
`

### Python SDK Usage

`python
import asyncio
from termux_aichain import LocalAgent, ToolRegistry

async def main():
    agent = LocalAgent(model="qwen2.5-0.5b")
    response = await agent.run("Check battery and temperature status.")
    print("Agent Response:", response)

asyncio.run(main())
`

### Node.js Installation

`ash
npm install termux-aichain
`

---

## 📚 Official Documentation

- **Official Web Documentation**: [https://uno-km.vercel.app/lib/aichain/](https://uno-km.vercel.app/lib/aichain/)
- **GitHub Repository**: [https://github.com/uno-km/termux-aichain](https://github.com/uno-km/termux-aichain)
- **License**: MIT