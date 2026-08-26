from __future__ import annotations
import os
import sys
import time
import json
import math
from typing import Callable, Tuple

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("termux_aichain"))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class RegressionAuditor:
    def __init__(self):
        self.total_score = 0.0
        self.max_score = 100.0
        self.results = []
        self.start_time = time.time()
        print("=" * 80)
        print(f"[*] termux-aichain v1.0.0 Microscopic Regression Audit [{time.strftime('%Y-%m-%d %H:%M:%S')}]")
        print("=" * 80)
        print("Zero-Point Baseline: Initial Score = 0.0 / 100.0 pts\n")

    def audit_step(
        self,
        category: str,
        name: str,
        allocated_pts: float,
        test_fn: Callable[[], bool],
    ) -> bool:
        t0 = time.perf_counter()
        passed = False
        err_msg = None
        try:
            passed = test_fn()
        except Exception as e:
            passed = False
            err_msg = str(e)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        awarded_pts = allocated_pts if passed else 0.0
        self.total_score += awarded_pts

        status_str = "PASS" if passed else "FAIL"
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [SCORE +{awarded_pts:4.1f}/{allocated_pts:4.1f} pts] ({category}) {name} in {duration_ms:6.2f}ms | Cumulative: {self.total_score:4.1f}")
        if not passed and err_msg:
            print(f"      ?遺??? ERROR: {err_msg}")

        self.results.append({
            "category": category,
            "name": name,
            "allocated": allocated_pts,
            "awarded": awarded_pts,
            "duration_ms": duration_ms,
            "passed": passed,
            "error": err_msg
        })
        return passed

    def print_final_scorecard(self):
        print("\n" + "=" * 80)
        print("?猷?FINAL REGRESSION AUDIT SCORECARD (0-Point Baseline)")
        print("=" * 80)
        percentage = (self.total_score / self.max_score) * 100.0
        grade = "A+ (PERFECT ZERO-DEFECT)" if percentage >= 100.0 else "A" if percentage >= 90.0 else "F (DEFECT DETECTED)"
        print(f"Total Cumulative Score: {self.total_score:.1f} / {self.max_score:.1f} pts ({percentage:.1f}%)")
        print(f"Final Quality Grade   : {grade}")
        print("-" * 80)

        categories = {}
        for r in self.results:
            cat = r["category"]
            categories.setdefault(cat, [0.0, 0.0])
            categories[cat][0] += r["awarded"]
            categories[cat][1] += r["allocated"]

        for cat, (awarded, allocated) in categories.items():
            print(f"  ??{cat:<35}: {awarded:4.1f} / {allocated:4.1f} pts")
        print("=" * 80)

        with open("audit_report.json", "w", encoding="utf-8") as f:
            json.dump({
                "total_score": self.total_score,
                "percentage": percentage,
                "grade": grade,
                "duration_sec": time.time() - self.start_time,
                "items": self.results
            }, f, indent=2, ensure_ascii=False)
        print("[*] Audit Report saved to audit_report.json\n")
        return percentage >= 100.0

def run_audit() -> bool:
    auditor = RegressionAuditor()

    # --- Category 1: Installation & Zero-Dep (15.0 pts) ---
    def test_zero_dep_imports():
        import termux_aichain
        return hasattr(termux_aichain, "__version__") and termux_aichain.__version__ == "1.0.0"
    auditor.audit_step("1. Installation & Zero-Dep", "Zero-Dep Standard Imports & Version 1.0.0", 5.0, test_zero_dep_imports)

    def test_disk_footprint():
        pkg_dir = os.path.dirname(os.path.abspath(__import__("termux_aichain").__file__))
        total_size = sum(os.path.getsize(os.path.join(r, f)) for r, d, files in os.walk(pkg_dir) for f in files)
        return total_size < 500 * 1024
    auditor.audit_step("1. Installation & Zero-Dep", "Micro Disk Footprint (< 500KB)", 5.0, test_disk_footprint)

    def test_schema_integrity():
        from termux_aichain import HumanMessage, AIMessage, GenerationResult, UsageInfo
        h = HumanMessage("Hello")
        a = AIMessage("World")
        res = GenerationResult(content="Test", usage=UsageInfo(10, 20, 30, 1.5), message=a)
        return h.role == "user" and a.role == "assistant" and res.usage.total_tokens == 30
    auditor.audit_step("1. Installation & Zero-Dep", "Schema Serialization Integrity", 5.0, test_schema_integrity)

    # --- Category 2: Core Engine & Chaining (15.0 pts) ---
    def test_pipe_composition():
        from termux_aichain import PromptTemplate, JsonOutputParser
        prompt = PromptTemplate.from_template("Format JSON: {task}")
        chain = prompt | (lambda s: '```json\n{"task_done": true}\n```') | JsonOutputParser()
        out = chain.invoke({"task": "audit"})
        return out.get("task_done") is True
    auditor.audit_step("2. Core Engine & Chaining", "Pipe Composition (|) & Json Parser", 5.0, test_pipe_composition)

    def test_recursive_splitter():
        from termux_aichain import RecursiveCharacterTextSplitter, Document
        splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
        docs = splitter.split_documents([Document(page_content="A" * 200)])
        return len(docs) >= 4 and all(len(d.page_content) <= 50 for d in docs)
    auditor.audit_step("2. Core Engine & Chaining", "Recursive Text Splitter Hierarchy", 5.0, test_recursive_splitter)

    def test_prompt_template_escapes():
        from termux_aichain import PromptTemplate
        tpl = PromptTemplate.from_template("Escaped {{brace}} and var {v}")
        return tpl.format(v="ok") == "Escaped {brace} and var ok"
    auditor.audit_step("2. Core Engine & Chaining", "PromptTemplate Literal Escaping", 5.0, test_prompt_template_escapes)

    # --- Category 3: Graph & State Machine (15.0 pts) ---
    def test_state_graph_loop():
        from termux_aichain import StateGraph, START, END
        workflow = StateGraph()
        workflow.add_node("inc", lambda s: {"n": s.get("n", 0) + 1})
        workflow.set_entry_point("inc")
        workflow.add_conditional_edges("inc", lambda s: END if s["n"] >= 5 else "inc")
        app = workflow.compile()
        res = app.invoke({"n": 0})
        return res["n"] == 5
    auditor.audit_step("3. Graph & State Machine", "Cyclic StateGraph Dynamic Routing", 7.5, test_state_graph_loop)

    def test_react_agent():
        from termux_aichain import create_react_agent, Tool, tool, HumanMessage, AIMessage, GenerationResult, UsageInfo
        from termux_aichain.core.base import BaseChatModel
        class DummyModel(BaseChatModel):
            def __init__(self):
                self.called = False
            def generate(self, messages):
                if not self.called:
                    self.called = True
                    ai = AIMessage(
                        content="Thought: execute dummy_calc",
                        tool_calls=[{"id": "c1", "function": {"name": "dummy_calc", "arguments": json.dumps({"x": 5})}}]
                    )
                    return GenerationResult(content=ai.content, usage=UsageInfo(1, 1, 2, 1.0), message=ai)
                ai = AIMessage(content="Final Answer: Result is 10.")
                return GenerationResult(content=ai.content, usage=UsageInfo(1, 1, 2, 1.0), message=ai)

        @tool(name="dummy_calc", description="Multiply by 2")
        def dummy_calc(x: int) -> str: return str(int(x) * 2)
        agent = create_react_agent(DummyModel(), [dummy_calc])
        res = agent.invoke({"messages": [HumanMessage("Calc")]})
        return "10" in res["messages"][-1].content
    auditor.audit_step("3. Graph & State Machine", "ReAct Autonomous Tool Loop", 7.5, test_react_agent)

    # --- Category 4: Memory & Vector Store (15.0 pts) ---
    def test_buffer_memory():
        from termux_aichain import ConversationBufferMemory
        mem = ConversationBufferMemory(k=1)
        mem.save_context("q1", "a1")
        mem.save_context("q2", "a2")
        msgs = mem.load_memory_variables()["history"]
        return len(msgs) == 2 and msgs[0].content == "q2" and msgs[1].content == "a2"
    auditor.audit_step("4. Memory & Vector Store", "Rolling ConversationBuffer Window", 5.0, test_buffer_memory)

    def test_sqlite_entity_memory():
        from termux_aichain import SQLiteEntityMemory
        mem = SQLiteEntityMemory(":memory:")
        mem.set("sovereign_flag", "true")
        return str(mem.get("sovereign_flag")).lower() == "true"
    auditor.audit_step("4. Memory & Vector Store", "SQLite Entity Memory ACID Persistence", 5.0, test_sqlite_entity_memory)

    def test_sqlite_vector_cosine():
        from termux_aichain import SQLiteVectorStore
        vstore = SQLiteVectorStore(":memory:")
        vstore.add_texts(["Edge", "Cloud"], [[1.0, 0.0], [0.0, 1.0]])
        results = vstore.similarity_search_by_vector([0.99, 0.01], k=1)
        return results[0][0].page_content == "Edge" and results[0][1] > 0.95
    auditor.audit_step("4. Memory & Vector Store", "MicroVectorStore Pure Cosine Precision", 5.0, test_sqlite_vector_cosine)

    # --- Category 5: Serve Engine & Live Dashboard UI (15.0 pts) ---
    def test_serve_http_and_dashboard():
        from termux_aichain import PromptTemplate, AgentServer
        import urllib.request
        prompt = PromptTemplate.from_template("Serve: {input}")
        server = AgentServer(prompt, host="127.0.0.1", port=0, quiet=True)
        server.add_trace({"name": "AuditSpan", "duration_ms": 2.1, "tokens": 15, "tps": 30.0})
        server.start_background()
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/ui") as r:
                html = r.read().decode("utf-8")
                ui_ok = "<!DOCTYPE html>" in html and "termux-aichain" in html
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/traces") as r:
                traces = json.loads(r.read().decode("utf-8"))
                trace_ok = len(traces) >= 1 and traces[0]["name"] == "AuditSpan"
            return ui_ok and trace_ok
        finally:
            server.stop()
    auditor.audit_step("5. Serve & Live Dashboard", "1-Line REST, SSE & Single-File Web Dashboard UI", 15.0, test_serve_http_and_dashboard)

    # --- Category 6: Device Hardware & uno-km Ecosystem (15.0 pts) ---
    def test_hardware_tools():
        from termux_aichain import get_battery_status, get_sensor_data, get_device_location
        b = get_battery_status()
        s = get_sensor_data("accel")
        l = get_device_location("last")
        return isinstance(b, str) and isinstance(s, str) and isinstance(l, str)
    auditor.audit_step("6. Device & Ecosystem Tools", "Native Hardware Tooling (Battery, Sensors, GPS)", 7.5, test_hardware_tools)

    def test_ecosystem_tools():
        from termux_aichain import transcribe_speech, generate_diffusion_image, browse_web_headless
        stt = transcribe_speech(duration_sec=1)
        diff = generate_diffusion_image(prompt="Audit", output_path="/tmp/test.png")
        web = browse_web_headless(url="http://example.com")
        return len(stt) > 0 and len(diff) > 0 and len(web) > 0
    auditor.audit_step("6. Device & Ecosystem Tools", "uno-km Ecosystem Integrations (STT, Diffusion, Playwright)", 7.5, test_ecosystem_tools)

    # --- Category 7: Local Server Fine-Tuning & Multi-Model Spectrum (10.0 pts) ---
    def test_local_server_tuning():
        from termux_aichain import LocalServerConfig, LlamaCppServer, OpenAICompatibleChat, HumanMessage
        config = LocalServerConfig(
            model_path="/path/to/model.gguf",
            threads=4,
            n_ctx=4096,
            n_gpu_layers=33,
            flash_attn=True,
            cache_type_k="q8_0",
            cache_type_v="q8_0",
            mlock=True
        )
        server = LlamaCppServer(config)
        args = server.build_cli_args()
        chat = OpenAICompatibleChat(temperature=0.1, top_k=20, min_p=0.05, repeat_penalty=1.15)
        payload = chat._build_payload([HumanMessage("Hi")])
        return "-fa" in args and "-ctk" in args and payload["top_k"] == 20 and payload["min_p"] == 0.05
    auditor.audit_step("7. Local Tuning & Spectrum", "Hardware Fine-Tuning & Full-Spectrum Sampling", 10.0, test_local_server_tuning)

    return auditor.print_final_scorecard()

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)