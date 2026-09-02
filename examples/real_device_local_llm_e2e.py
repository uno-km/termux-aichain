#!/usr/bin/env python3
"""
termux-aichain Real-Device On-Device LLM & Agent End-to-End Test
Manages local llama-server lifecycle and verifies complete AI chaining on Samsung Galaxy S20.
Zero fake simulation strings - 100% Ground Truth native execution & diagnostics.
"""

import sys
import os
import time
import subprocess
import urllib.request
import json

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from termux_aichain import (
    OpenAICompatibleChat,
    ChatPromptTemplate,
    JsonOutputParser,
    Tracer,
    create_react_agent,
    get_battery_status,
    HumanMessage
)

from pathlib import Path

LLAMA_SERVER_BIN = os.environ.get("TERMUX_LLAMA_BIN", str(Path.home() / ".termux-llama" / "bin" / "llama-server"))
LLAMA_MODEL_PATH = os.environ.get("TERMUX_LLAMA_MODEL", str(Path.home() / ".termux-llama" / "models" / "Llama-3.2-3B-Instruct-Q4_K_M.gguf"))
PORT = 8088

def wait_for_server(port: int, max_wait: float = 20.0) -> bool:
    start_t = time.time()
    url = f"http://127.0.0.1:{port}/health"
    while time.time() - start_t < max_wait:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    print("=" * 64)
    print("[RUN] termux-aichain Real-Device Local LLM Integration Suite")
    print("=" * 64)

    server_proc = None
    if os.path.exists(LLAMA_SERVER_BIN) and os.path.exists(LLAMA_MODEL_PATH):
        print(f"[*] Launching local llama-server on port {PORT} (Threads: 4, Ctx: 1024)...")
        server_cmd = [
            LLAMA_SERVER_BIN,
            "-m", LLAMA_MODEL_PATH,
            "-t", "4",
            "-c", "1024",
            "--port", str(PORT),
            "--host", "127.0.0.1"
        ]
        server_proc = subprocess.Popen(server_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] Waiting for model loading into memory...")
        if wait_for_server(PORT, max_wait=20.0):
            print("[*] Model loaded successfully. Local server is ready.")
        else:
            raise RuntimeError(f"Local llama-server failed to bind and become healthy on port {PORT}.")
    else:
        print("[INFO] Target binary or model weights not found at default path. Connecting to running endpoint if available.")

    try:
        base_url = f"http://127.0.0.1:{PORT}/v1"
        llm = OpenAICompatibleChat(
            base_url=base_url,
            model="Llama-3.2-3B-Instruct",
            temperature=0.2,
            max_tokens=80,
            timeout=30.0
        )

        tracer = Tracer("GalaxyS20_Native_LLM_Run")

        print("\n--- [Step 1: Real-time SSE Token Streaming] ---")
        with tracer.trace("Local_LLM_Streaming"):
            print("Response: ", end="", flush=True)
            for chunk in llm.stream("In 1 short sentence, what is sovereign on-device AI?"):
                print(chunk.delta, end="", flush=True)
            print()

        print("\n--- [Step 2: Structured JSON Chaining (| Operator)] ---")
        with tracer.trace("Pipeline_JsonParsing"):
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a concise edge AI. Reply strictly with JSON: {{\"status\": \"ok\", \"benefit\": \"low_latency\"}}"),
                ("user", "What is the top benefit of running AI locally on mobile? Reply in JSON format.")
            ])
            chain = prompt | llm | JsonOutputParser()
            res = chain.invoke({})
            print("Parsed Result:", res)

        print("\n--- [Step 3: Autonomous Hardware Tool Agent (ReAct)] ---")
        with tracer.trace("ReAct_Device_Agent"):
            agent = create_react_agent(
                model=llm,
                tools=[get_battery_status],
                system_prompt="You are an Android assistant. Check battery status when requested."
            )
            state = agent.invoke(
                {"messages": [HumanMessage(content="Check battery level.")]}
            )
            print("Agent Final Response:", state["messages"][-1].content)

        tracer.finish()

        print("\n" + "=" * 64)
        print("[TRACER] On-Device Execution Latency Profile")
        print("=" * 64)
        print(tracer.render_tree())
        print("=" * 64)
        print("[SUCCESS] Real hardware LLM execution completed.")

    finally:
        if server_proc:
            print("\n[*] Stopping llama-server...")
            server_proc.terminate()
            server_proc.wait(timeout=5.0)
            print("[*] llama-server stopped.")

if __name__ == "__main__":
    main()