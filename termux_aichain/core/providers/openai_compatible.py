"""
==============================================================================
termux-aichain OpenAI Compatible Provider
==============================================================================
Provides high-performance, zero-dependency REST & SSE streaming interface
compatible with llama-server, bitnet.cpp, Ollama, Exo, and OpenAI endpoints.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
import urllib.parse
import asyncio
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Union
from termux_aichain.core.schema import Message, AIMessage, GenerationResult, StreamChunk, UsageInfo
from termux_aichain.core.base import BaseChatModel

class OpenAICompatibleChat(BaseChatModel):
    """Zero-dependency Chat Model supporting llama-server, bitnet.cpp, Ollama, and OpenAI."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        api_key: Optional[str] = None,
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: float = 60.0,
        headers: Optional[Dict[str, str]] = None,
        **extra_kwargs: Any
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "no-key"
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra_kwargs = extra_kwargs

        self.custom_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        if headers:
            self.custom_headers.update(headers)

    def _format_payload_messages(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        if isinstance(messages, str):
            formatted.append({"role": "user", "content": messages})
        elif isinstance(messages, Sequence):
            for m in messages:
                if isinstance(m, Message):
                    formatted.append(m.to_dict())
                elif isinstance(m, dict):
                    formatted.append(m)
                else:
                    raise TypeError(f"Invalid message type in sequence: {type(m)}")
        else:
            raise TypeError(f"Invalid messages argument type: {type(messages)}")
        return formatted

    def _build_payload(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], stream: bool = False, **kwargs: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": self._format_payload_messages(messages),
            "temperature": kwargs.get("temperature", self.temperature),
            "stream": stream,
            **self.extra_kwargs
        }
        max_tok = kwargs.get("max_tokens", self.max_tokens)
        if max_tok is not None:
            payload["max_tokens"] = max_tok
        for k, v in kwargs.items():
            if k not in payload and k not in ("model", "temperature", "max_tokens"):
                payload[k] = v
        return payload

    def generate(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> GenerationResult:
        payload = self._build_payload(messages, stream=False, **kwargs)
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.custom_headers,
            method="POST"
        )
        t_start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                raw_bytes = resp.read()
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                data = json.loads(raw_bytes.decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAICompatibleChat HTTPError {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAICompatibleChat Request Failed: {str(e)}") from e

        choices = data.get("choices", [])
        if not choices:
            raise ValueError(f"No choices returned from model endpoint: {data}")

        choice = choices[0]
        msg_dict = choice.get("message", {})
        content = msg_dict.get("content", "")
        tool_calls = msg_dict.get("tool_calls")

        usage_raw = data.get("usage", {})
        usage = UsageInfo(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
            latency_ms=round(elapsed_ms, 2)
        )

        ai_msg = AIMessage(content=content, tool_calls=tool_calls)
        return GenerationResult(content=content, message=ai_msg, usage=usage, raw=data)

    async def agenerate(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> GenerationResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.generate(messages, **kwargs))

    def stream(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> Iterator[StreamChunk]:
        payload = self._build_payload(messages, stream=True, **kwargs)
        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.custom_headers,
            method="POST"
        )
        t_start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                accumulated_content: List[str] = []
                for line_bytes in resp:
                    line = line_bytes.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                            yield StreamChunk(
                                content="".join(accumulated_content),
                                delta="",
                                is_last=True,
                                usage=UsageInfo(latency_ms=round(elapsed_ms, 2))
                            )
                            break
                        try:
                            parsed = json.loads(data_str)
                            choices = parsed.get("choices", [])
                            if choices:
                                delta_dict = choices[0].get("delta", {})
                                delta_text = delta_dict.get("content", "")
                                if delta_text:
                                    accumulated_content.append(delta_text)
                                    yield StreamChunk(
                                        content="".join(accumulated_content),
                                        delta=delta_text,
                                        is_last=False,
                                        raw=parsed
                                    )
                        except json.JSONDecodeError:
                            continue
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAICompatibleChat Stream HTTPError {e.code}: {err_msg}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAICompatibleChat Stream Failed: {str(e)}") from e

    async def astream(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> AsyncIterator[StreamChunk]:
        # Generator bridge for async streaming
        queue: asyncio.Queue[Optional[Union[StreamChunk, Exception]]] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _sync_worker() -> None:
            try:
                for chunk in self.stream(messages, **kwargs):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as ex:
                loop.call_soon_threadsafe(queue.put_nowait, ex)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        asyncio.create_task(asyncio.to_thread(_sync_worker))

        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    def __repr__(self) -> str:
        return f"OpenAICompatibleChat(base_url='{self.base_url}', model='{self.model}')"