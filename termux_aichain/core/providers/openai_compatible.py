"""
==============================================================================
termux-aichain Core Engine: Advanced OpenAI-Compatible & Local LLM Provider
==============================================================================
Provides high-performance REST and SSE streaming interface with full-spectrum
sampling controls (temperature, top_p, top_k, min_p, repeat_penalty, grammar, seed).
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import json
import time
import asyncio
import urllib.request
import urllib.error
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union
from termux_aichain.core.base import BaseChatModel
from termux_aichain.core.schema import (
    Message,
    HumanMessage,
    AIMessage,
    SystemMessage,
    GenerationResult,
    StreamChunk,
    UsageInfo,
)

class OpenAICompatibleChat(BaseChatModel):
    """Full-featured chat provider for llama.cpp, BitNet.cpp, vLLM, Ollama, and OpenAI API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        api_key: str = "sk-termux-sovereign",
        model: str = "local-model",
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40,
        min_p: float = 0.05,
        repeat_penalty: float = 1.1,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        max_tokens: int = 512,
        stop: Optional[List[str]] = None,
        seed: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        grammar: Optional[str] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.min_p = min_p
        self.repeat_penalty = repeat_penalty
        self.presence_penalty = presence_penalty
        self.frequency_penalty = frequency_penalty
        self.max_tokens = max_tokens
        self.stop = stop or []
        self.seed = seed
        self.response_format = response_format
        self.grammar = grammar
        self.extra_body = extra_body or {}
        self.timeout = timeout

    def _coerce_messages(self, input_data: Union[str, List[Message], Dict[str, Any]]) -> List[Message]:
        if isinstance(input_data, str):
            return [HumanMessage(content=input_data)]
        elif isinstance(input_data, list):
            return input_data
        elif isinstance(input_data, dict):
            if "messages" in input_data:
                return input_data["messages"]
            elif "input" in input_data:
                return [HumanMessage(content=str(input_data["input"]))]
            return [HumanMessage(content=json.dumps(input_data))]
        return [HumanMessage(content=str(input_data))]

    def _build_payload(self, messages: List[Message], stream: bool = False) -> Dict[str, Any]:
        msgs_payload = [m.to_dict() for m in messages]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": msgs_payload,
            "stream": stream,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
        }
        if self.top_k > 0:
            payload["top_k"] = self.top_k
        if self.min_p > 0.0:
            payload["min_p"] = self.min_p
        if self.repeat_penalty != 1.0:
            payload["repeat_penalty"] = self.repeat_penalty
        if self.presence_penalty != 0.0:
            payload["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty != 0.0:
            payload["frequency_penalty"] = self.frequency_penalty
        if self.stop:
            payload["stop"] = self.stop
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.response_format is not None:
            payload["response_format"] = self.response_format
        if self.grammar:
            payload["grammar"] = self.grammar

        for k, v in self.extra_body.items():
            payload[k] = v

        return payload

    def generate(self, messages: List[Message]) -> GenerationResult:
        url = f"{self.base_url}/chat/completions"
        payload = self._build_payload(messages, stream=False)
        req_data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST"
        )

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                choice = resp_json.get("choices", [{}])[0]
                msg = choice.get("message", {})
                content = msg.get("content", "")
                
                raw_usage = resp_json.get("usage", {})
                latency_ms = max(0.01, (time.time() - t0) * 1000.0)
                usage = UsageInfo(
                    prompt_tokens=raw_usage.get("prompt_tokens", 0),
                    completion_tokens=raw_usage.get("completion_tokens", 0),
                    total_tokens=raw_usage.get("total_tokens", 0),
                    latency_ms=latency_ms,
                )
                return GenerationResult(content=content, usage=usage, message=AIMessage(content=content))
        except urllib.error.HTTPError as ex:
            err_body = ex.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {ex.code} from local LLM provider: {err_body}")
        except Exception as ex:
            raise RuntimeError(f"Failed to connect to local LLM at {url}: {str(ex)}")

    async def agenerate(self, messages: List[Message]) -> GenerationResult:
        return await asyncio.to_thread(self.generate, messages)

    def stream(self, input_data: Union[str, List[Message], Dict[str, Any]]) -> Iterator[StreamChunk]:
        messages = self._coerce_messages(input_data)
        url = f"{self.base_url}/chat/completions"
        payload = self._build_payload(messages, stream=True)
        req_data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                accumulated = ""
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield StreamChunk(delta="", content=accumulated, is_last=True)
                            break
                        try:
                            chunk_json = json.loads(data_str)
                            choice = chunk_json.get("choices", [{}])[0]
                            delta_content = choice.get("delta", {}).get("content", "")
                            if delta_content:
                                accumulated += delta_content
                                yield StreamChunk(delta=delta_content, content=accumulated, is_last=False)
                        except json.JSONDecodeError:
                            continue
        except Exception as ex:
            raise RuntimeError(f"Streaming error from local LLM at {url}: {str(ex)}")

    async def astream(self, input_data: Union[str, List[Message], Dict[str, Any]]) -> AsyncIterator[StreamChunk]:
        for chunk in await asyncio.to_thread(lambda: list(self.stream(input_data))):
            yield chunk