"""
Unit tests for termux_aichain.serve (AgentServer & serve helper)
"""
import json
import time
import urllib.request
import pytest
from termux_aichain.core.base import RunnableLambda
from termux_aichain.core.prompt import PromptTemplate
from termux_aichain.serve.server import AgentServer, serve

@pytest.fixture
def running_server():
    # Simple echo chain
    prompt = PromptTemplate.from_template("Served Agent says: {message}")
    chain = prompt | (lambda x: {"response": x.upper()})
    
    server = AgentServer(runnable=chain, host="127.0.0.1", port=0, quiet=True)
    server.start_background()
    port = server.server_address[1]
    time.sleep(0.05)
    
    yield f"http://127.0.0.1:{port}"
    
    server.stop()

def test_server_health(running_server):
    req = urllib.request.Request(f"{running_server}/health", method="GET")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["engine"] == "termux-aichain"

def test_server_invoke(running_server):
    payload = {"input": {"message": "hello termux"}}
    req = urllib.request.Request(
        f"{running_server}/invoke",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["output"]["response"] == "SERVED AGENT SAYS: HELLO TERMUX"

def test_server_stream_sse(running_server):
    payload = {"input": {"message": "streaming"}}
    req = urllib.request.Request(
        f"{running_server}/stream",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        assert resp.status == 200
        lines = []
        for line_bytes in resp:
            line = line_bytes.decode("utf-8").strip()
            if line:
                lines.append(line)
            if line == "data: [DONE]":
                break
        assert any("SERVED AGENT SAYS: STREAMING" in l for l in lines)
        assert "data: [DONE]" in lines