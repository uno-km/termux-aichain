"""
==============================================================================
termux-aichain Serve Engine: 1-Line REST & SSE Serving (LangServe Alternative)
==============================================================================
Zero-dependency HTTP REST, SSE, and Live Dashboard server for hosting
chains, agents, and runnables on local mobile network.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Union
from termux_aichain.core.base import Runnable
from termux_aichain.core.schema import Message, AIMessage, GenerationResult, StreamChunk
from termux_aichain.serve.dashboard import DASHBOARD_HTML

class _AgentRequestHandler(BaseHTTPRequestHandler):
    server: AgentServer  # type: ignore

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_GET(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        
        # 1. Root / UI Dashboard
        if path in ("", "/", "/ui", "/dashboard"):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        # 2. Health Endpoint
        if path == "/health":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "engine": "termux-aichain", "version": "0.1.0"}).encode())
            return

        # 3. Live Traces API
        if path == "/api/traces":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.server.recent_traces, ensure_ascii=False).encode())
            return

        # 4. StateGraph Topology API
        if path == "/api/graph":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            graph_meta = {
                "type": type(self.server.runnable).__name__,
                "nodes": getattr(self.server.runnable, "nodes", {}).keys() if hasattr(self.server.runnable, "nodes") else [],
                "edges": list(getattr(self.server.runnable, "edges", {}).items()) if hasattr(self.server.runnable, "edges") else []
            }
            self.wfile.write(json.dumps(graph_meta).encode())
            return

        self.send_response(404)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint {path} not found."}).encode())

    def do_POST(self) -> None:
        path = self.path.split("?")[0].rstrip("/")
        prefix = self.server.endpoint_prefix.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            payload = {}

        input_data = payload.get("input", payload)

        if path == f"{prefix}/invoke" or path == "/invoke":
            try:
                result = self.server.runnable.invoke(input_data)
                serialized = self._serialize_output(result)

                res_bytes = json.dumps({"output": serialized}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(res_bytes)))
                self.end_headers()
                self.wfile.write(res_bytes)
            except Exception as ex:
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(ex)}).encode("utf-8"))

        elif path == f"{prefix}/stream" or path == "/stream":
            try:
                self.send_response(200)
                self._send_cors_headers()
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()

                for chunk in self.server.runnable.stream(input_data):
                    chunk_serialized = self._serialize_output(chunk)
                    data_line = f"data: {json.dumps(chunk_serialized, ensure_ascii=False)}\n\n"
                    self.wfile.write(data_line.encode("utf-8"))
                    self.wfile.flush()

                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True
            except Exception as ex:
                err_line = f"data: {json.dumps({'error': str(ex)})}\n\n"
                self.wfile.write(err_line.encode("utf-8"))
                self.wfile.flush()
                self.close_connection = True
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Path {path} not recognized."}).encode())

    def _serialize_output(self, output: Any) -> Any:
        if isinstance(output, (AIMessage, Message)):
            return output.to_dict()
        elif isinstance(output, GenerationResult):
            return {"content": output.content, "usage": output.usage.__dict__ if output.usage else {}}
        elif isinstance(output, StreamChunk):
            return {"delta": output.delta, "content": output.content, "is_last": output.is_last}
        elif isinstance(output, (dict, list, str, int, float, bool)) or output is None:
            return output
        elif isinstance(output, tuple) and len(output) == 2:
            return {"node": output[0], "state": self._serialize_output(output[1])}
        return str(output)

    def log_message(self, format: str, *args: Any) -> None:
        if self.server.quiet:
            return
        super().log_message(format, *args)

class AgentServer(HTTPServer):
    """Zero-dependency HTTP, SSE & Live Dashboard Server for Runnables and Agents."""

    def __init__(
        self,
        runnable: Runnable,
        host: str = "0.0.0.0",
        port: int = 8080,
        endpoint_prefix: str = "",
        quiet: bool = True
    ):
        self.runnable = runnable
        self.endpoint_prefix = endpoint_prefix
        self.quiet = quiet
        self.recent_traces: List[Dict[str, Any]] = []
        super().__init__((host, port), _AgentRequestHandler)
        self._thread: Optional[threading.Thread] = None

    def add_trace(self, trace_dict: Dict[str, Any]) -> None:
        self.recent_traces.insert(0, trace_dict)
        if len(self.recent_traces) > 50:
            self.recent_traces.pop()

    def start_background(self) -> None:
        """Starts the server in a daemon background thread."""
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops and closes the server cleanly."""
        self.shutdown()
        self.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

def serve(
    runnable: Runnable,
    host: str = "0.0.0.0",
    port: int = 8080,
    endpoint_prefix: str = "",
    block: bool = True
) -> AgentServer:
    """1-Line helper to expose any Runnable, Chain, or Agent over HTTP, SSE & Web Dashboard."""
    server = AgentServer(
        runnable=runnable,
        host=host,
        port=port,
        endpoint_prefix=endpoint_prefix,
        quiet=False
    )
    if block:
        print(f"[*] termux-aichain serving agent on http://{host}:{port}{endpoint_prefix}")
        print(f"[*] Web Dashboard UI: http://{host}:{port}/ui (Live SSE Chat & Tracer)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Shutting down agent server...")
        finally:
            server.stop()
    else:
        server.start_background()
    return server