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
        assert data["service"] == "termux-aichain"

def test_server_auth_and_body_limits():
    prompt = PromptTemplate.from_template("Echo: {message}")
    chain = prompt | (lambda x: {"response": x})
    server = AgentServer(runnable=chain, host="127.0.0.1", port=0, api_key="secret_token", max_body_bytes=100, quiet=True)
    server.start_background()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"

    try:
        # 1. Unauthorized request
        req1 = urllib.request.Request(f"{url}/invoke", data=b'{"input":{"message":"hi"}}', method="POST")
        try:
            urllib.request.urlopen(req1)
            assert False, "Should raise 401"
        except urllib.error.HTTPError as ex:
            assert ex.code == 401

        # 2. Authorized request
        req2 = urllib.request.Request(
            f"{url}/invoke",
            data=b'{"input":{"message":"hi"}}',
            headers={"Authorization": "Bearer secret_token", "Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req2) as resp2:
            assert resp2.status == 200

        # 3. Payload size limit exceeded (413)
        req3 = urllib.request.Request(
            f"{url}/invoke",
            data=json.dumps({"input": {"message": "A" * 200}}).encode("utf-8"),
            headers={"Authorization": "Bearer secret_token", "Content-Type": "application/json"},
            method="POST"
        )
        try:
            urllib.request.urlopen(req3)
            assert False, "Should raise 413"
        except urllib.error.HTTPError as ex:
            assert ex.code == 413
    finally:
        server.stop()

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

def test_cors_exact_loopback_and_subdomain_rejection(running_server):
    # 1. Valid loopback origins
    for valid_origin in ["http://localhost:3000", "http://127.0.0.1:5173"]:
        req = urllib.request.Request(f"{running_server}/health", headers={"Origin": valid_origin}, method="GET")
        with urllib.request.urlopen(req) as resp:
            assert resp.headers.get("Access-Control-Allow-Origin") == valid_origin

    # 2. Evil subdomain tricks
    for evil_origin in ["http://localhost.evil.example", "http://127.0.0.1.evil.example", "not-a-valid-origin"]:
        req = urllib.request.Request(f"{running_server}/health", headers={"Origin": evil_origin}, method="GET")
        with urllib.request.urlopen(req) as resp:
            # Must NOT reflect the evil origin
            assert resp.headers.get("Access-Control-Allow-Origin") != evil_origin

def test_server_invalid_json_body_returns_400(running_server):
    req = urllib.request.Request(
        f"{running_server}/invoke",
        data=b'{"input": { broken json',
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        assert False, "Should raise 400 HTTPError"
    except urllib.error.HTTPError as ex:
        assert ex.code == 400