import os
import time
import math
import json
import unittest.mock
import pytest
from termux_aichain import (
    LocalAgent,
    ConnectConfig,
    ManagedConfig,
    ToolPolicy,
    ToolRule,
    AgentState,
    vibrate_device,
    get_battery_status,
    HumanMessage,
    ServerConnectionRefusedError,
    ServerProtocolMismatchError,
    ModelIdentityMismatchError,
    RemoteFallbackNotAuthorizedError,
    ToolApprovalRequiredError,
    ToolArgumentValidationError,
    ToolRateLimitExceededError,
    ToolPolicyDeniedError,
    ToolCallRepairNotAllowedError,
    DuplicateToolAliasError,
    DuplicateServerOwnershipError,
    LocalAgentError,
    SQLiteVectorStore,
    Tool,
    tool,
    create_react_agent
)
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import AIMessage, GenerationResult
from termux_aichain.core.local_agent import validate_loopback_endpoint, ServerIdentityVerifier, NoRedirectHandler
from termux_aichain.output.normalizer import OutputNormalizer, RawModelResponse, OutputParserPolicy, validate_tool_arguments

class StaticModel(BaseChatModel):
    def __init__(self, content: str = ""):
        self.content = content
    def generate(self, messages):
        return GenerationResult(content=self.content, message=AIMessage(content=self.content))

class SequenceModel(BaseChatModel):
    def __init__(self, responses):
        self.responses = list(responses)
        self.idx = 0
    def generate(self, messages):
        resp = self.responses[min(self.idx, len(self.responses) - 1)]
        self.idx += 1
        return GenerationResult(content=resp, message=AIMessage(content=resp))

# 1. Bash fence 내부 JSON이 ToolCall로 승격되지 않음 (P0-1 완결 검증)
def test_json_inside_bash_fence_is_not_promoted():
    raw = RawModelResponse(
        provider="test",
        model="test",
        text="""
Example only:
```bash
echo '{"tool":"termux_vibrate", "arguments":{"duration_ms":1500}}'
```
"""
    )
    result = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert result.type == "text"
    assert result.tool_calls == []
    assert any("code_block_excluded_from_tool_parsing" in w for w in result.warnings)

# 2. Python fence 내부 JSON도 승격되지 않음
def test_json_inside_python_fence_not_promoted():
    raw = RawModelResponse(
        provider="test",
        model="test",
        text="""
```python
payload = {"name": "termux_vibrate", "arguments": {"duration_ms": 1000}}
```
"""
    )
    result = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert result.type == "text"
    assert result.tool_calls == []

# 3. ReAct 사용법 예시가 기본 비활성화로 실행되지 않음
def test_react_example_not_promoted_by_default():
    raw = RawModelResponse(
        provider="generic",
        model="test",
        text='Usage example:\nAction: termux_vibrate\nAction Input: {"duration_ms": 1500}'
    )
    # Default policy has allow_react_text_tool_calls=False
    result = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert result.type == "text"
    assert result.tool_calls == []

# 4. 인용된 Action/Input이 실행되지 않음
def test_quoted_action_input_not_promoted():
    raw = RawModelResponse(
        provider="generic",
        model="test",
        text='The user said: "Action: termux_vibrate is a hardware tool".'
    )
    result = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert result.type == "text"
    assert result.tool_calls == []

# 5. force="false"가 boolean으로 수용되지 않음 (P0-3 JSON Schema 검증)
def test_string_false_rejected_for_boolean():
    schema = {
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer"},
            "force": {"type": "boolean"}
        },
        "required": ["duration_ms"]
    }
    with pytest.raises(ToolArgumentValidationError) as exc:
        validate_tool_arguments(schema, {"duration_ms": 500, "force": "false"})
    assert "must be a boolean" in str(exc.value)

# 6. 필수 tool argument 누락 시 실행 전 거부
def test_missing_required_tool_arg_rejected():
    schema = {
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer"}
        },
        "required": ["duration_ms"]
    }
    with pytest.raises(ToolArgumentValidationError) as exc:
        validate_tool_arguments(schema, {})
    assert "Missing required argument" in str(exc.value)

# 7. unknown argument 거부
def test_unknown_tool_arg_rejected():
    schema = {
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer"}
        },
        "required": ["duration_ms"],
        "additionalProperties": False
    }
    with pytest.raises(ToolArgumentValidationError) as exc:
        validate_tool_arguments(schema, {"duration_ms": 500, "malicious_payload": "hack"})
    assert "Unknown arguments" in str(exc.value)

# 8. localhost.evil.example 거부 (P0-5 Loopback URL 검사)
def test_loopback_prefix_bypass_rejected():
    with pytest.raises(ServerConnectionRefusedError):
        validate_loopback_endpoint("http://localhost.evil.example:8080")
    with pytest.raises(ServerConnectionRefusedError):
        validate_loopback_endpoint("http://127.0.0.1.evil.com:8080")
    with pytest.raises(ServerConnectionRefusedError):
        validate_loopback_endpoint("http://0.0.0.0:8080")

# 9. localhost@evil.example 거부
def test_loopback_userinfo_bypass_rejected():
    with pytest.raises(ServerConnectionRefusedError):
        validate_loopback_endpoint("http://localhost@evil.example:8080")

# 10. invalid health JSON 거부 (P0-6 Fail-Closed Handshake)
def test_invalid_health_json_rejected(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b"Not A Valid JSON <html/>"
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    with pytest.raises(ServerProtocolMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080")
    assert "not valid JSON" in str(exc.value)

# 11. empty health JSON 거부
def test_empty_health_json_rejected(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b"{}"
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    with pytest.raises(ServerProtocolMismatchError):
        ServerIdentityVerifier.verify("http://127.0.0.1:8080")

# 12. protocolVersion 누락·불일치 거부
def test_protocol_version_mismatch_rejected(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b'{"service": "llama-server", "protocolVersion": "99.0"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    with pytest.raises(ServerProtocolMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", expected_protocol_version="1.0")
    assert "Protocol version mismatch" in str(exc.value)

# 13. health payload 크기 초과 거부
def test_health_payload_size_exceeded_rejected(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b"A" * (limit + 10)
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    with pytest.raises(ServerProtocolMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", max_health_bytes=100)
    assert "exceeds maximum allowed size" in str(exc.value)

# 14. managed 기존 서버 model mismatch 거부
def test_managed_existing_model_mismatch(monkeypatch):
    class FakeResp:
        status = 200
        def read(self, limit):
            return b'{"service": "llama-server", "protocolVersion": "1.0", "model": {"id": "wrong-model.gguf"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    with pytest.raises(ModelIdentityMismatchError):
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", expected_model_id="expected-model.gguf")

# 15. stop과 invoke 경쟁에서 신규 요청 거부 (P0-9 상태 경쟁 방어)
def test_stopped_agent_rejects_invoke():
    agent = LocalAgent(
        mode="test",
        chat_model=StaticModel("ok"),
        tools=[]
    )
    agent.close()
    assert agent.state == AgentState.STOPPED
    with pytest.raises(LocalAgentError) as exc:
        agent.invoke({"messages": [HumanMessage(content="hi")]})
    assert "cannot accept requests" in str(exc.value)

# 16. remote mode가 미집행 정책으로 실행되지 않음 (P0-10 Option A)
def test_remote_mode_rc_disabled():
    with pytest.raises(RemoteFallbackNotAuthorizedError):
        LocalAgent.create(mode="remote")

# 17. 빈 embedding 거부 (P1 VectorStore 보완)
def test_empty_embedding_rejected():
    vstore = SQLiteVectorStore(db_path=":memory:")
    with pytest.raises(ValueError) as exc:
        vstore.add_texts(["text"], [[]])
    assert "must not be empty" in str(exc.value)
    vstore.close()

# 18. k 음수·과대·bool 거부
def test_invalid_k_rejected():
    vstore = SQLiteVectorStore(db_path=":memory:")
    vstore.add_texts(["text"], [[1.0, 0.0]])
    with pytest.raises(ValueError):
        vstore.similarity_search_by_vector([1.0, 0.0], k=True)
    with pytest.raises(ValueError):
        vstore.similarity_search_by_vector([1.0, 0.0], k=0)
    with pytest.raises(ValueError):
        vstore.similarity_search_by_vector([1.0, 0.0], k=1000)
    vstore.close()

# 19. 손상된 vector row가 전체 검색을 무너뜨리지 않음
def test_corrupted_vector_row_skipped():
    vstore = SQLiteVectorStore(db_path=":memory:")
    vstore.add_texts(["valid"], [[1.0, 0.0]])
    # Intentionally corrupt a row in DB
    with vstore.conn:
        vstore.conn.execute("INSERT INTO vector_documents (text, embedding, metadata, dimension) VALUES (?, ?, ?, ?)",
                            ("corrupted", "{corrupted_json", "{}", 2))
    hits = vstore.similarity_search_by_vector([1.0, 0.0], k=2)
    assert len(hits) == 1
    assert hits[0].page_content == "valid"
    vstore.close()

# 20. 진동 도구 force 타입 검사 및 범위 검증
def test_vibrate_device_force_type_check():
    with pytest.raises(ToolArgumentValidationError):
        vibrate_device(duration_ms=500, force="false")  # string "false" rejected

# 21. 기본 create_react_agent에서 ReAct 문구가 실행되지 않음 (P0-1)
def test_default_create_react_agent_no_react_text():
    model = StaticModel('Action: termux_vibrate\nAction Input: {"duration_ms": 500}')
    agent = create_react_agent(model=model, tools=[vibrate_device])
    res = agent.invoke({"messages": [HumanMessage(content="test")]})
    # Last message remains plain text AIMessage with no tool call
    last_msg = res["messages"][-1]
    assert isinstance(last_msg, AIMessage)
    assert not last_msg.tool_calls

# 22. 명시적으로 활성화한 경우에만 ReAct ToolCall 생성
def test_explicit_create_react_agent_allows_react_text():
    # SequenceModel: 1st returns action, 2nd returns final answer
    model = SequenceModel([
        'Action: termux_vibrate\nAction Input: {"duration_ms": 500}',
        'Vibration completed successfully.'
    ])
    agent = create_react_agent(
        model=model,
        tools=[vibrate_device],
        parser_policy=OutputParserPolicy(allow_react_text_tool_calls=True)
    )
    res = agent.invoke({"messages": [HumanMessage(content="test")]})
    assert any(m.__class__.__name__ == "ToolMessage" for m in res["messages"])

# 23. duration_ms minimum/maximum Schema 검증 (P0-2)
def test_duration_ms_min_max_schema_validation():
    schema = {
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer", "minimum": 50, "maximum": 2000}
        },
        "required": ["duration_ms"]
    }
    with pytest.raises(ToolArgumentValidationError) as exc1:
        validate_tool_arguments(schema, {"duration_ms": 10})
    assert "must be >= 50" in str(exc1.value)

    with pytest.raises(ToolArgumentValidationError) as exc2:
        validate_tool_arguments(schema, {"duration_ms": 5000})
    assert "must be <= 2000" in str(exc2.value)

# 24. Health HTTP Redirect 거부 (P1-1)
def test_health_redirect_rejected():
    # Test NoRedirectHandler
    handler = NoRedirectHandler()
    with pytest.raises(ServerProtocolMismatchError) as exc:
        handler.http_error_302(None, None, 302, "Found", {})
    assert "redirect" in str(exc.value)

# 25. 다른 모델이 같은 포트를 점유하면 spawn하지 않고 CONFLICT 오류 (P0-4)
def test_conflict_server_identity_blocks_spawn(monkeypatch, tmp_path):
    dummy_model = tmp_path / "my_model.gguf"
    dummy_model.write_text("dummy")

    class FakeConflictResp:
        status = 200
        def read(self, limit):
            return b'{"service": "llama-server", "protocolVersion": "1.0", "model": {"id": "conflicting_model.gguf"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeConflictResp())
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    # Attempting to create managed agent when conflicting model is running
    with pytest.raises(DuplicateServerOwnershipError) as exc:
        LocalAgent.create(mode="managed", model_path=str(dummy_model))
    assert "incompatible or conflicting" in str(exc.value)

# 26. STOPPING / STOPPED 상태에서 lease 획득 거부 (P1-3)
def test_stopping_state_rejects_lease():
    agent = LocalAgent(mode="test", chat_model=StaticModel(), tools=[])
    agent.close()
    assert agent.state == AgentState.STOPPED
    with pytest.raises(LocalAgentError) as exc:
        with agent.acquire_lease():
            pass
    assert "Cannot acquire lease" in str(exc.value)

# 27. Vector search heap 메모리 크기 k 바운딩 검증 (P1-4)
def test_vector_search_bounded_heap():
    vstore = SQLiteVectorStore(db_path=":memory:")
    # Add 50 items
    texts = [f"doc_{i}" for i in range(50)]
    embeddings = [[float(i), float(50 - i)] for i in range(50)]
    vstore.add_texts(texts, embeddings)

    results = vstore.similarity_search_by_vector([25.0, 25.0], k=3)
    assert len(results) == 3
    vstore.close()

# 28. status:ok 미식별 서버는 openai-compatible로 분류되며 llama-server로 오인하지 않음 (P0-3)
def test_unknown_server_status_ok_is_openai_compatible_not_llama(monkeypatch):
    class FakeGenericResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeGenericResp())
    payload = ServerIdentityVerifier.verify("http://127.0.0.1:8080")
    assert payload["service"] == "openai-compatible"

    # expected_service="llama-server" 지정 시 불일치로 거부
    with pytest.raises(ServerProtocolMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", expected_service="llama-server")
    assert "Service mismatch" in str(exc.value)

# 29. expected_model_id 지정 + 서버 model ID 누락 시 fail-closed (P0-2)
def test_expected_model_id_missing_fails_closed(monkeypatch):
    class FakeNoModelResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok", "service": "termux-aichain"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeNoModelResp())
    with pytest.raises(ModelIdentityMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", expected_model_id="qwen-2.5-1.5b")
    assert "Expected model ID was configured, but the server did not provide model identity" in str(exc.value)

# 30. expected_model_sha256 지정 + 서버 checksum 누락 시 fail-closed (P0-2)
def test_expected_model_sha256_missing_fails_closed(monkeypatch):
    class FakeNoChecksumResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok", "service": "termux-aichain", "model": {"id": "qwen-2.5-1.5b"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeNoChecksumResp())
    with pytest.raises(ModelIdentityMismatchError) as exc:
        ServerIdentityVerifier.verify("http://127.0.0.1:8080", expected_model_sha256="abcdef123456")
    assert "Expected model SHA-256 was configured, but the server did not provide a checksum" in str(exc.value)

# 31. managed OWNED 생성 성공 및 status.runtime_ownership == OWNED (P0-1)
def test_managed_owned_lifecycle_and_status(monkeypatch, tmp_path):
    model_file = tmp_path / "qwen2.5.gguf"
    model_file.write_text("model_data")

    # Fake server health check & spawn
    class FakeResp:
        status = 200
        def read(self, limit):
            return b'{"status": "ok", "service": "llama-server", "protocolVersion": "1.0", "model": {"id": "qwen2.5.gguf"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.OpenerDirector.open", lambda self, req, timeout: FakeResp())
    monkeypatch.setattr("shutil.which", lambda bin_name: "/usr/bin/" + bin_name)
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: unittest.mock.MagicMock(pid=9999, poll=lambda: None))

    agent = LocalAgent(
        mode="managed",
        chat_model=unittest.mock.MagicMock(),
        tools=[],
        owns_managed_process=True,
        runtime_ownership="OWNED"
    )
    try:
        st = agent.status()
        assert st["runtime_ownership"] == "OWNED"
        assert st["mode"] == "managed"
    finally:
        agent.close()

# 32. managed ATTACHED 생성 성공 및 close 시 외부 자원 보존 (P0-1)
def test_managed_attached_lifecycle_preserves_external(monkeypatch, tmp_path):
    lock_file = tmp_path / "server.lock"
    lock_file.write_text(json.dumps({"pid": 8888, "endpoint": "http://127.0.0.1:8080", "created_at": time.time()}))

    agent = LocalAgent(
        mode="managed",
        chat_model=unittest.mock.MagicMock(),
        tools=[],
        lock_file_path=lock_file,
        owns_managed_process=False,
        owns_identity_lock=False,
        runtime_ownership="ATTACHED"
    )
    st = agent.status()
    assert st["runtime_ownership"] == "ATTACHED"
    agent.close()
    # Lock file must remain preserved since agent was attached, not owned
    assert lock_file.exists()

# 33. BoundedRingLog 단일 초대형 로그 행(100KB) 상한 및 바이트 보장 (P0-2)
def test_ring_log_single_oversized_line_is_bounded():
    from termux_aichain.core.providers.local_server import BoundedRingLog
    log = BoundedRingLog(maxlen=200, max_bytes=65536)
    log.append("A" * 100_000)
    assert log._current_bytes <= 65536
    total_bytes = sum(len(line.encode("utf-8")) for line in log.lines)
    assert total_bytes <= 65536

# 34. managed 시작 실패 시 UnboundLocalError 없이 원본 예외 보존 (P0-3)
def test_managed_start_failure_preserves_original_error(monkeypatch, tmp_path):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model-data")
    monkeypatch.setattr("shutil.which", lambda name: f"/fake/{name}")

    def fail_start(self, *args, **kwargs):
        raise OSError("popen failed to execute binary")

    monkeypatch.setattr(
        "termux_aichain.core.providers.local_server.LocalServerManager.start",
        fail_start,
    )
    with pytest.raises(OSError, match="popen failed to execute binary"):
        LocalAgent.create(
            mode="managed",
            model_path=str(model)
        )

# 35. CORS scheme 및 userinfo 엄격 거부 (P1-3)
def test_cors_scheme_and_userinfo_rejected():
    from termux_aichain.serve.server import is_allowed_loopback_origin
    assert is_allowed_loopback_origin("http://localhost:3000") is True
    assert is_allowed_loopback_origin("http://127.0.0.1:8080") is True
    assert is_allowed_loopback_origin("ftp://localhost") is False
    assert is_allowed_loopback_origin("file://localhost/foo") is False
    assert is_allowed_loopback_origin("http://admin:pass@localhost:3000") is False
    assert is_allowed_loopback_origin("http://localhost.evil.example") is False
    assert is_allowed_loopback_origin("") is False

# 36. Missing protocolVersion in /health fails closed (P0-3)
def test_missing_protocol_version_fails_closed(monkeypatch):
    import io
    from termux_aichain.core.local_agent import ServerIdentityVerifier, ServerProtocolMismatchError
    class FakeHealthResp:
        status = 200
        def read(self, size): return b'{"status":"ok","service":"termux-aichain"}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    class FakeOpener:
        def open(self, *args, **kwargs): return FakeHealthResp()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())

    with pytest.raises(ServerProtocolMismatchError, match="Server did not report a protocol version"):
        ServerIdentityVerifier.verify(
            endpoint_url="http://127.0.0.1:8080",
            expected_protocol_version="1.0"
        )

# 37. LocalAgent.local() does not swallow model identity conflict (P0-2)
def test_local_agent_local_does_not_swallow_model_conflict(monkeypatch, tmp_path):
    import io
    from termux_aichain.core.local_agent import LocalAgent, DuplicateServerOwnershipError
    class FakeHealthResp:
        status = 200
        def read(self, size): return b'{"status":"ok","service":"termux-aichain","protocolVersion":"1.0","model":{"id":"other-model.gguf"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    class FakeOpener:
        def open(self, *args, **kwargs): return FakeHealthResp()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: FakeHealthResp())

    # Create dummy local model
    m = tmp_path / "target-model.gguf"
    m.write_bytes(b"GGUF_TEST")

    with pytest.raises(DuplicateServerOwnershipError, match="Existing server at http://127.0.0.1:8080 conflicts"):
        LocalAgent.local(str(m))

# 38. LocalAgent.local() missing model raises FileNotFoundError (P0-2)
def test_local_agent_local_missing_model_raises_file_not_found(monkeypatch):
    import urllib.error
    from termux_aichain.core.local_agent import LocalAgent
    class FailingOpener:
        def open(self, *args, **kwargs): raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FailingOpener())
    with pytest.raises(FileNotFoundError, match="was not found in ~/models"):
        LocalAgent.local("completely-non-existent-model")

# 39. cmd_run rejects user-specified non-GGUF file (P1-3)
def test_cmd_run_rejects_non_gguf_user_file(tmp_path, capsys):
    from termux_aichain.cli import cmd_run
    bad_file = tmp_path / "malicious.bin"
    bad_file.write_bytes(b"NOT_A_GGUF_HEADER")
    cmd_run(str(bad_file))
    out = capsys.readouterr().out
    assert "not a valid GGUF binary format" in out