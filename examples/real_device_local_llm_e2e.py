#!/usr/bin/env python3
"""
termux-aichain Real-Device On-Device LLM & Agent End-to-End Test
Executes inference with local llama-server on Samsung Galaxy S20.
"""

import sys
import os
import time

# Auto-inject project root
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

def run_local_llm_e2e():
    print("================================================================")
    print("⚡ termux-aichain Real-Device Local LLM Integration Test")
    print("================================================================")

    # 1. Connect to local llama-server
    base_url = "http://127.0.0.1:8088/v1"
    llm = OpenAICompatibleChat(
        base_url=base_url,
        model="Llama-3.2-3B-Instruct",
        temperature=0.1,
        max_tokens=150
    )

    tracer = Tracer("GalaxyS20_E2E_Run")

    print("\n[*] 1. Testing Direct Streaming Generation...")
    with tracer.trace("LLM_Streaming_Generation"):
        print("Model Response: ", end="", flush=True)
        token_count = 0
        for chunk in llm.stream("State 2 key benefits of edge computing in 1 short sentence."):
            print(chunk.delta, end="", flush=True)
            token_count += 1
        print()

    print("\n[*] 2. Testing Pipeline with JSON Parser (| operator)...")
    with tracer.trace("Pipeline_JsonParsing"):
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a concise edge assistant. Reply strictly in JSON: {\"status\": \"ok\", \"insight\": \"...\"}"),
            ("user", "Summarize mobile AI potential.")
        ])
        chain = prompt | llm | JsonOutputParser()
        result = chain.invoke({})
        print("Parsed JSON Result:", result)

    print("\n[*] 3. Testing Hardware Tool Calling Agent (Battery Status)...")
    with tracer.trace("ReAct_Hardware_Agent"):
        # We supply the real Android battery tool
        agent = create_react_agent(model=llm, tools=[get_battery_status])
        state = agent.invoke({"messages": [HumanMessage(content="Check device battery level and report it.")]}, max_iterations=3)
        print("Agent Final Message:", state["messages"][-1].content)

    tracer.finish()

    print("\n================================================================")
    print("📊 CLI Execution Tree & Performance Profile")
    print("================================================================")
    tracer.print_tree()
    print("================================================================")

if __name__ == "__main__":
    run_local_llm_e2e()