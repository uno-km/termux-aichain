"""
==============================================================================
termux-aichain Microscopic Edge Case & Boundary Verification Suite
==============================================================================
Tests extreme boundary conditions, malformed payloads, zero-division,
deep recursion limits, and fault tolerance across all core modules.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

import json
import pytest
from termux_aichain import (
    PromptTemplate,
    ChatPromptTemplate,
    JsonOutputParser,
    RecursiveCharacterTextSplitter,
    Document,
    StateGraph,
    START,
    END,
    ConversationBufferMemory,
    SQLiteEntityMemory,
    SQLiteVectorStore,
    Tracer,
    OpenAICompatibleChat,
    LocalServerConfig,
    LlamaCppServer,
    get_battery_status,
    transcribe_speech,
    generate_diffusion_image,
    browse_web_headless,
)

# ------------------------------------------------------------------------------
# 1. Core Module Boundary Tests
# ------------------------------------------------------------------------------
def test_edge_prompt_template_special_chars():
    tpl = PromptTemplate.from_template("Literal {{escaped}} and var: {input} with \n\t and Special: !@#$%^&*()")
    res = tpl.format(input="test_input")
    assert "{escaped}" in res
    assert "test_input" in res
    assert "Special" in res

def test_edge_json_parser_malformed():
    parser = JsonOutputParser()
    # Case 1: Plain markdown code block with trailing text
    res1 = parser.parse("```json\n{\"status\": \"ok\", \"val\": 123}\n```\nSome trailing explanation.")
    assert res1 == {"status": "ok", "val": 123}
    
    # Case 2: Broken JSON with parser throwing ValueError
    with pytest.raises(ValueError):
        parser.parse("Not a JSON at all {broken")

    # Case 3: Parser with default fallback factory
    fallback_parser = JsonOutputParser(default_factory=lambda: {"fallback": True})
    res3 = fallback_parser.parse("Totally broken output")
    assert res3 == {"fallback": True}

def test_edge_recursive_splitter_large_text():
    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
    large_text = ("Termux Sovereign AI Chain for Android Edge. " * 500) # ~22KB
    docs = splitter.split_documents([Document(page_content=large_text)])
    assert len(docs) > 50
    for doc in docs:
        assert len(doc.page_content) <= 120

# ------------------------------------------------------------------------------
# 2. Graph Engine Boundary Tests
# ------------------------------------------------------------------------------
def test_edge_graph_uncompiled_or_missing_entry():
    workflow = StateGraph()
    workflow.add_node("step", lambda s: s)
    with pytest.raises(Exception):
        workflow.compile() # No entry point

def test_edge_graph_recursion_limit():
    workflow = StateGraph()
    workflow.add_node("infinite_loop", lambda s: {"count": s.get("count", 0) + 1})
    workflow.set_entry_point("infinite_loop")
    workflow.add_edge("infinite_loop", "infinite_loop")
    app = workflow.compile()
    
    with pytest.raises(RuntimeError, match="exceeded maximum iteration safety limit"):
        app.invoke({"count": 0}, max_iterations=15)

# ------------------------------------------------------------------------------
# 3. Memory & Vector Store Zero-Division / Math Edge Cases
# ------------------------------------------------------------------------------
def test_edge_vector_store_zero_norm():
    vstore = SQLiteVectorStore(":memory:")
    # Inserting a zero vector [0.0, 0.0, 0.0]
    vstore.add_texts(
        texts=["Zero Vector Document", "Normal Vector"],
        embeddings=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    )
    # Searching should NOT raise ZeroDivisionError
    res = vstore.similarity_search_by_vector([1.0, 0.0, 0.0], k=2)
    assert len(res) >= 1
    assert res[0][0].page_content == "Normal Vector"

def test_edge_entity_memory_null_and_overwrite():
    mem = SQLiteEntityMemory(":memory:")
    mem.set("key1", "val1")
    assert mem.get("key1") == "val1"
    # Overwrite
    mem.set("key1", "val2")
    assert mem.get("key1") == "val2"
    # Non-existent
    assert mem.get("non_existent_key") is None

# ------------------------------------------------------------------------------
# 4. Tracer Deep Hierarchy Tests
# ------------------------------------------------------------------------------
def test_edge_tracer_deep_nesting():
    tracer = Tracer("RootSpan")
    # 8 levels deep nesting
    with tracer.trace("Level_1"):
        with tracer.trace("Level_2"):
            with tracer.trace("Level_3"):
                with tracer.trace("Level_4"):
                    with tracer.trace("Level_5"):
                        with tracer.trace("Level_6"):
                            with tracer.trace("Level_7"):
                                with tracer.trace("Level_8") as s:
                                    s.finish(tokens=5)
    tracer.finish()
    tree = tracer.render_tree()
    assert "Level_8" in tree
    assert "RootSpan" in tree

# ------------------------------------------------------------------------------
# 5. Device & Ecosystem Fault-Tolerance Tests
# ------------------------------------------------------------------------------
def test_edge_ecosystem_fault_tolerance():
    # Negative duration
    stt_res = transcribe_speech(duration_sec=-1)
    assert isinstance(stt_res, str)
    
    # Empty prompt diffusion
    diff_res = generate_diffusion_image(prompt="", output_path="/tmp/empty.png")
    assert isinstance(diff_res, str)
    
    # Invalid URL headless browse
    web_res = browse_web_headless(url="not_a_valid_url", query="abc")
    assert isinstance(web_res, str)