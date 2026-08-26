"""
Unit tests for termux_aichain.serve.dashboard (Live HTML & Trace/Graph APIs)
"""
import json
import urllib.request
import pytest
from termux_aichain.core.prompt import PromptTemplate
from termux_aichain.serve.server import AgentServer

@pytest.fixture
def running_dashboard_server():
    prompt = PromptTemplate.from_template("Dashboard Echo: {input}")
    server = AgentServer(runnable=prompt, host="127.0.0.1", port=0, quiet=True)
    server.add_trace({"name": "InitSpan", "duration_ms": 1.5, "tokens": 10, "tps": 20.0})
    server.start_background()
    port = server.server_address[1]
    
    yield f"http://127.0.0.1:{port}"
    
    server.stop()

def test_dashboard_html_endpoint(running_dashboard_server):
    with urllib.request.urlopen(f"{running_dashboard_server}/ui") as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "<!DOCTYPE html>" in content
        assert "termux-aichain" in content
        assert "Live Monitor" in content

def test_api_traces_endpoint(running_dashboard_server):
    with urllib.request.urlopen(f"{running_dashboard_server}/api/traces") as resp:
        assert resp.status == 200
        traces = json.loads(resp.read().decode("utf-8"))
        assert isinstance(traces, list)
        assert len(traces) >= 1
        assert traces[0]["name"] == "InitSpan"

def test_api_graph_endpoint(running_dashboard_server):
    with urllib.request.urlopen(f"{running_dashboard_server}/api/graph") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "type" in data