"""
==============================================================================
termux-aichain Core Engine: Runnable Base & Pipe Composition (|)
==============================================================================
Provides standard Runnable, RunnableLambda, RunnableSequence interfaces.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import inspect
import asyncio
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Union
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, GenerationResult, StreamChunk

class Runnable(ABC):
    """Abstract Base Class for all executable chains, templates, and models."""

    @abstractmethod
    def invoke(self, input_data: Any, **kwargs: Any) -> Any:
        pass

    async def ainvoke(self, input_data: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.invoke, input_data, **kwargs)

    def stream(self, input_data: Any, **kwargs: Any) -> Iterator[Any]:
        yield self.invoke(input_data, **kwargs)

    async def astream(self, input_data: Any, **kwargs: Any) -> AsyncIterator[Any]:
        yield await self.ainvoke(input_data, **kwargs)

    def __or__(self, other: Union[Runnable, Callable[[Any], Any]]) -> RunnableSequence:
        right = other if isinstance(other, Runnable) else RunnableLambda(other)
        return RunnableSequence(self, right)

    def __ror__(self, other: Union[Runnable, Callable[[Any], Any]]) -> RunnableSequence:
        left = other if isinstance(other, Runnable) else RunnableLambda(other)
        return RunnableSequence(left, self)

class RunnableLambda(Runnable):
    """Wraps any standard Python callable into a pipe-compatible Runnable."""

    def __init__(self, func: Callable[[Any], Any]):
        self.func = func

    def invoke(self, input_data: Any, **kwargs: Any) -> Any:
        if kwargs:
            return self.func(input_data, **kwargs)
        return self.func(input_data)

    async def ainvoke(self, input_data: Any, **kwargs: Any) -> Any:
        if inspect.iscoroutinefunction(self.func):
            return await self.func(input_data, **kwargs)
        return await asyncio.to_thread(self.invoke, input_data, **kwargs)

class RunnableSequence(Runnable):
    """Executes multiple Runnables sequentially in a linear pipe chain."""

    def __init__(self, *steps: Runnable):
        self.steps: List[Runnable] = []
        for step in steps:
            if isinstance(step, RunnableSequence):
                self.steps.extend(step.steps)
            elif isinstance(step, Runnable):
                self.steps.append(step)
            elif callable(step):
                self.steps.append(RunnableLambda(step))
            else:
                raise TypeError(f"Invalid step in sequence: {type(step)}")

    def invoke(self, input_data: Any, **kwargs: Any) -> Any:
        current = input_data
        for step in self.steps:
            current = step.invoke(current, **kwargs)
        return current

    async def ainvoke(self, input_data: Any, **kwargs: Any) -> Any:
        current = input_data
        for step in self.steps:
            current = await step.ainvoke(current, **kwargs)
        return current

    def stream(self, input_data: Any, **kwargs: Any) -> Iterator[Any]:
        if not self.steps:
            return
        if len(self.steps) == 1:
            yield from self.steps[0].stream(input_data, **kwargs)
            return

        current = input_data
        for step in self.steps[:-1]:
            current = step.invoke(current, **kwargs)

        yield from self.steps[-1].stream(current, **kwargs)

    async def astream(self, input_data: Any, **kwargs: Any) -> AsyncIterator[Any]:
        if not self.steps:
            return
        if len(self.steps) == 1:
            async for chunk in self.steps[0].astream(input_data, **kwargs):
                yield chunk
            return

        current = input_data
        for step in self.steps[:-1]:
            current = await step.ainvoke(current, **kwargs)

        async for chunk in self.steps[-1].astream(current, **kwargs):
            yield chunk

    def __or__(self, other: Union[Runnable, Callable[[Any], Any]]) -> RunnableSequence:
        right = other if isinstance(other, Runnable) else RunnableLambda(other)
        return RunnableSequence(*self.steps, right)

class BaseChatModel(Runnable, ABC):
    """Abstract Base Class for Chat Models."""

    @abstractmethod
    def generate(self, messages: List[Message]) -> GenerationResult:
        pass

    async def agenerate(self, messages: List[Message]) -> GenerationResult:
        return await asyncio.to_thread(self.generate, messages)

    def invoke(self, input_data: Union[str, List[Message], Dict[str, Any]], **kwargs: Any) -> GenerationResult:
        messages = self._coerce_messages(input_data)
        return self.generate(messages)

    async def ainvoke(self, input_data: Union[str, List[Message], Dict[str, Any]], **kwargs: Any) -> GenerationResult:
        messages = self._coerce_messages(input_data)
        return await self.agenerate(messages)

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
            return [HumanMessage(content=str(input_data))]
        return [HumanMessage(content=str(input_data))]