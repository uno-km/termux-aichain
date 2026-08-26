"""
Unit tests for termux_aichain.trace (Tracer, TraceSpan, traceable)
"""
import os
import tempfile
import time
import pytest
from termux_aichain.trace.tracer import Tracer, TraceSpan, traceable

def test_tracer_hierarchy_and_tps():
    tracer = Tracer(root_name="RootPipeline")
    
    with tracer.trace("PromptFormatting") as s1:
        time.sleep(0.01)
        
    with tracer.trace("LLMInference", model="bitnet-b1.58") as s2:
        time.sleep(0.02)
        s2.finish(outputs="Generated response", tokens=50)
        
    tracer.finish()
    
    assert len(tracer.root_span.children) == 2
    assert tracer.root_span.children[0].name == "PromptFormatting"
    assert tracer.root_span.children[1].name == "LLMInference"
    assert tracer.root_span.children[1].tokens == 50
    assert tracer.root_span.children[1].tps > 0.0

def test_tracer_render_tree():
    tracer = Tracer(root_name="AgentExecution")
    with tracer.trace("ThinkStep") as s:
        with tracer.trace("ToolCall: BatteryCheck") as s_child:
            s_child.finish(outputs="88%")
            
    tracer.finish()
    tree = tracer.render_tree(use_color=False)
    
    assert "AgentExecution" in tree
    assert "ThinkStep" in tree
    assert "ToolCall: BatteryCheck" in tree

def test_tracer_export_jsonl():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as tmp:
        log_path = tmp.name
        
    try:
        tracer = Tracer(root_name="ExportTest")
        with tracer.trace("SubStep"):
            pass
        tracer.finish()
        tracer.export_jsonl(log_path)
        
        with open(log_path, "r", encoding="utf-8") as f:
            line = f.readline()
            assert "ExportTest" in line
            assert "SubStep" in line
    finally:
        if os.path.exists(log_path):
            os.remove(log_path)