"""
Unit tests for termux_aichain.core.providers.openai_compatible (using Mock HTTP Server)
"""
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pytest
from termux_aichain.core.providers.openai_compatible import OpenAICompatibleChat
from termux_aichain.core.schema import HumanMessage, SystemMessage

class MockOpenAIServer(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        payload = json.loads(body)
        is_stream = payload.get("stream", False)
        
        if not is_stream:
            response_data = {
                "id": "chatcmpl-mock-123",
                "object": "chat.completion",
                "created": 1700000000,
                "model": payload.get("model", "mock-model"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello from mock BitNet edge server!"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20
                }
            }
            res_bytes = json.dumps(response_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(res_bytes)))
            self.end_headers()
            self.wfile.write(res_bytes)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            
            tokens = ["Hello", " from", " streaming", " Termux", " model!"]
            for token in tokens:
                chunk = {
                    "id": "chatcmpl-stream-123",
                    "object": "chat.completion.chunk",
                    "choices": [{
                        "index": 0,
                        "delta": {"content": token},
                        "finish_reason": None
                    }]
                }
                line = f"data: {json.dumps(chunk)}\n\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
            
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

    def log_message(self, format, *args):
        # Suppress server logging during tests
        return

@pytest.fixture(scope="module")
def mock_server():
    server = HTTPServer(("127.0.0.1", 0), MockOpenAIServer)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/v1"
    server.shutdown()
    server.server_close()

def test_openai_compatible_generate(mock_server):
    client = OpenAICompatibleChat(base_url=mock_server, model="bitnet-b1.58-3b")
    messages = [
        SystemMessage(content="You are an edge assistant."),
        HumanMessage(content="Hi")
    ]
    res = client.generate(messages)
    assert res.content == "Hello from mock BitNet edge server!"
    assert res.usage.prompt_tokens == 12
    assert res.usage.completion_tokens == 8
    assert res.usage.total_tokens == 20
    assert res.usage.latency_ms > 0

def test_openai_compatible_stream(mock_server):
    client = OpenAICompatibleChat(base_url=mock_server, model="bitnet-b1.58-3b")
    chunks = list(client.stream("Hi stream"))
    
    assert len(chunks) == 6 # 5 deltas + 1 [DONE] chunk
    deltas = [c.delta for c in chunks if not c.is_last]
    full_text = "".join(deltas)
    assert full_text == "Hello from streaming Termux model!"
    assert chunks[-1].is_last is True