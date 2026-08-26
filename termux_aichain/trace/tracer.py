"""
==============================================================================
termux-aichain Trace Engine: Lightweight CLI Observability & Latency Profiler
==============================================================================
Provides hierarchical execution traces, token counters, TPS meters, and
colorful console tree outputs without cloud LangSmith overhead.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import time
import json
import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

@dataclass
class TraceSpan:
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    inputs: Any = None
    outputs: Any = None
    tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List[TraceSpan] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.perf_counter()
        return round((end - self.start_time) * 1000.0, 2)

    @property
    def tps(self) -> float:
        dur_s = self.duration_ms / 1000.0
        if dur_s <= 0 or self.tokens <= 0:
            return 0.0
        return round(self.tokens / dur_s, 2)

    def finish(self, outputs: Any = None, tokens: int = 0, error: Optional[Exception] = None) -> None:
        self.end_time = time.perf_counter()
        self.outputs = outputs
        if tokens > 0:
            self.tokens = tokens
        if error:
            self.error = str(error)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "tokens": self.tokens,
            "tps": self.tps,
            "error": self.error,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children]
        }

class _SpanContext:
    def __init__(self, tracer: Tracer, span: TraceSpan):
        self.tracer = tracer
        self.span = span

    def __enter__(self) -> TraceSpan:
        return self.span

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_val:
            self.span.finish(error=exc_val)
        else:
            self.span.finish()
        self.tracer._pop_span(self.span)

class Tracer:
    """Zero-dependency execution tracer and profiler for chains and agents."""

    def __init__(self, root_name: str = "Execution"):
        self.root_name = root_name
        self.root_span = TraceSpan(name=root_name)
        self._current_stack: List[TraceSpan] = [self.root_span]

    @property
    def root(self) -> TraceSpan:
        return self.root_span

    def trace(self, name: str, inputs: Any = None, **metadata: Any) -> _SpanContext:
        span = TraceSpan(name=name, inputs=inputs, metadata=metadata)
        parent = self._current_stack[-1]
        parent.children.append(span)
        self._current_stack.append(span)
        return _SpanContext(self, span)

    def _pop_span(self, span: TraceSpan) -> None:
        if self._current_stack and self._current_stack[-1] == span:
            self._current_stack.pop()

    def finish(self, outputs: Any = None) -> None:
        self.root_span.finish(outputs=outputs)

    def render_tree(self, use_color: bool = True) -> str:
        lines: List[str] = []
        c_cyan = "\033[36m" if use_color else ""
        c_green = "\033[32m" if use_color else ""
        c_yellow = "\033[33m" if use_color else ""
        c_red = "\033[31m" if use_color else ""
        c_reset = "\033[0m" if use_color else ""

        def _walk(span: TraceSpan, prefix: str = "", is_last: bool = True, is_root: bool = False) -> None:
            marker = "" if is_root else ("└── " if is_last else "├── ")
            tok_info = f", {span.tokens} tok ({span.tps} TPS)" if span.tokens > 0 else ""
            err_info = f" {c_red}[ERROR: {span.error}]{c_reset}" if span.error else ""
            line = f"{prefix}{marker}{c_cyan}{span.name}{c_reset} {c_green}[{span.duration_ms} ms{tok_info}]{c_reset}{err_info}"
            lines.append(line)

            child_prefix = prefix + ("    " if is_last else "│   ")
            if is_root:
                child_prefix = ""
            for idx, child in enumerate(span.children):
                is_last_child = idx == (len(span.children) - 1)
                _walk(child, child_prefix, is_last_child, False)

        _walk(self.root_span, is_root=True)
        return "\n".join(lines)

    def export_jsonl(self, filepath: str) -> None:
        """Appends trace tree to a local JSONL log file for offline profiling."""
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(self.root_span.to_dict(), ensure_ascii=False) + "\n")

    def get_flat_spans(self) -> List[TraceSpan]:
        flat: List[TraceSpan] = []
        def _flatten(span: TraceSpan):
            flat.append(span)
            for c in span.children:
                _flatten(c)
        _flatten(self.root_span)
        return flat

def traceable(name: Optional[str] = None) -> Callable[..., Any]:
    """Decorator to automatically wrap a function or method in a trace span."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        span_name = name or fn.__name__
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = Tracer(root_name=span_name)
            with tracer.trace(span_name, inputs={"args": str(args), "kwargs": str(kwargs)}):
                return fn(*args, **kwargs)
        return wrapper
    return decorator