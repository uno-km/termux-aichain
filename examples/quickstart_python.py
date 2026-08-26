#!/usr/bin/env python3
"""
termux-aichain Phase 1 Quickstart Example
Runs a complete zero-dependency pipeline without external packages.
"""

import sys
import os

# Auto-inject project root into sys.path for instant standalone execution
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from termux_aichain import (
    PromptTemplate,
    ChatPromptTemplate,
    OpenAICompatibleChat,
    JsonOutputParser,
    StringOutputParser,
    RecursiveCharacterTextSplitter
)

def demo_pipeline():
    print("=== 1. Prompt Template Test ===")
    prompt = PromptTemplate.from_template("Task: {task} on device {device}")
    formatted = prompt.format(task="Monitor Battery", device="Galaxy S20")
    print("Formatted:", formatted)

    print("\n=== 2. Functional Chain Pipeline (| operator) ===")
    step1 = prompt
    step2 = lambda text: f"[PROCESSED] {text.upper()}"
    chain = step1 | step2
    res = chain.invoke({"task": "Optimize NPU", "device": "ARM64"})
    print("Chain Result:", res)

    print("\n=== 3. JSON Output Parser Test ===")
    parser = JsonOutputParser()
    raw_llm_response = """```json
{
  "status": "success",
  "recommended_model": "bitnet-b1.58-3b",
  "vram_mb": 420
}
```"""
    parsed = parser.invoke(raw_llm_response)
    print("Parsed JSON:", parsed)

    print("\n=== 4. Recursive Character Text Splitter Test ===")
    splitter = RecursiveCharacterTextSplitter(chunk_size=40, chunk_overlap=5)
    sample_text = (
        "Termux AI Chain is engineered for edge computing.\n"
        "Zero dependencies ensure instant cold start on mobile devices."
    )
    chunks = splitter.split_text(sample_text)
    for i, c in enumerate(chunks):
        print(f"Chunk #{i}: {c!r}")

if __name__ == "__main__":
    demo_pipeline()