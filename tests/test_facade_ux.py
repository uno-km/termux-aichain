"""
Unit tests for termux_aichain Sovereign Facade API & Progressive Disclosure UX
"""
import pytest
import unittest.mock
from termux_aichain import LocalAgent, HumanMessage, AIMessage

def test_local_agent_default_constructor(monkeypatch):
    class FakeChat:
        def generate(self, messages, **kwargs):
            return unittest.mock.MagicMock(message=AIMessage("Battery level is 88%."))

    agent = LocalAgent()
    assert agent.mode == "connect"
    assert agent.status()["state"] == "READY"

def test_local_agent_run_facade(monkeypatch):
    class FakeChat:
        def generate(self, messages, **kwargs):
            return unittest.mock.MagicMock(message=AIMessage("Everything is operational."))

    agent = LocalAgent(chat_model=FakeChat())
    response = agent.run("Check system status")
    assert isinstance(response, str)
    assert "Everything is operational." in response

def test_local_agent_connect_factory(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok", "service": "termux-aichain", "protocolVersion": "1.0"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    agent = LocalAgent.connect("http://127.0.0.1:8080")
    assert agent.mode == "connect"
    assert agent.status()["mode"] == "connect"

def test_local_agent_local_factory_when_server_alive(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok", "service": "llama-server", "protocolVersion": "1.0", "model": {"id": "qwen2.5-1.5b"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    agent = LocalAgent.local("qwen2.5-1.5b")
    assert agent.mode == "connect"