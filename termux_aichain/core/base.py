"""
==============================================================================
termux-aichain Core Runnable & Base Abstractions
==============================================================================
Provides the unified Runnable protocol, pipe (|) operator, sequential chain,
and base chat model abstraction.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import abc
import asyncio
import inspect
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Sequence, TypeVar, Union
from termux_aichain.core.schema import Message, HumanMessage, AIMessage, GenerationResult, StreamChunk
from termux_aichain.core.prompt import PromptTemplate, ChatPromptTemplate

Input = TypeVar("Input")
Output = TypeVar("Output")
Other = TypeVar("Other")

class Runnable(abc.ABC):
    """Abstract base class for all runnable pipeline components."""

    @abc.abstractmethod
    def invoke(self, input_val: Any, **kwargs: Any) -> Any:
        """Synchronously processes input and returns the result."""
        pass

    async def ainvoke(self, input_val: Any, **kwargs: Any) -> Any:
        """Asynchronously processes input and returns the result."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.invoke(input_val, **kwargs))

    def stream(self, input_val: Any, **kwargs: Any) -> Iterator[Any]:
        """Synchronously streams chunks from input."""
        res = self.invoke(input_val, **kwargs)
        yield res

    async def astream(self, input_val: Any, **kwargs: Any) -> AsyncIterator[Any]:
        """Asynchronously streams chunks from input."""
        res = await self.ainvoke(input_val, **kwargs)
        yield res

    def pipe(self, *others: Union[Runnable, Callable[[Any], Any]]) -> RunnableSequence:
        """Chains this runnable with other runnables or callables with auto-flattening."""
        steps: List[Runnable] = []
        if isinstance(self, RunnableSequence):
            steps.extend(self.steps)
        else:
            steps.append(self)

        for other in others:
            if isinstance(other, RunnableSequence):
                steps.extend(other.steps)
            elif isinstance(other, Runnable):
                steps.append(other)
            elif callable(other):
                steps.append(RunnableLambda(other))
            else:
                raise TypeError(f"Cannot pipe with object of type: {type(other)}")
        return RunnableSequence(steps=steps)

    def __or__(self, other: Union[Runnable, Callable[[Any], Any]]) -> RunnableSequence:
        return self.pipe(other)

    def __ror__(self, other: Any) -> Any:
        if callable(other) and not isinstance(other, Runnable):
            return RunnableLambda(other).pipe(self)
        raise TypeError(f"Unsupported operand for pipe: {type(other)}")

class RunnableLambda(Runnable):
    """Wraps a pure Python callable as a pipeline Runnable."""

    def __init__(self, func: Callable[[Any], Any]):
        self.func = func

    def invoke(self, input_val: Any, **kwargs: Any) -> Any:
        return self.func(input_val, **kwargs) if kwargs else self.func(input_val)

    async def ainvoke(self, input_val: Any, **kwargs: Any) -> Any:
        if inspect.iscoroutinefunction(self.func):
            return await self.func(input_val, **kwargs) if kwargs else await self.func(input_val)
        return self.invoke(input_val, **kwargs)

    def __repr__(self) -> str:
        name = getattr(self.func, "__name__", str(self.func))
        return f"RunnableLambda({name})"

class RunnableSequence(Runnable):
    """Executes a series of Runnables in sequential pipeline order."""

    def __init__(self, steps: Sequence[Runnable]):
        self.steps = list(steps)

    def invoke(self, input_val: Any, **kwargs: Any) -> Any:
        current = input_val
        for i, step in enumerate(self.steps):
            if i == 0 and kwargs:
                current = step.invoke(current, **kwargs)
            else:
                current = step.invoke(current)
        return current

    async def ainvoke(self, input_val: Any, **kwargs: Any) -> Any:
        current = input_val
        for i, step in enumerate(self.steps):
            if i == 0 and kwargs:
                current = await step.ainvoke(current, **kwargs)
            else:
                current = await step.ainvoke(current)
        return current

    def stream(self, input_val: Any, **kwargs: Any) -> Iterator[Any]:
        if not self.steps:
            return
        current = input_val
        for i, step in enumerate(self.steps[:-1]):
            if i == 0 and kwargs:
                current = step.invoke(current, **kwargs)
            else:
                current = step.invoke(current)
        last_step = self.steps[-1]
        yield from last_step.stream(current)

    async def astream(self, input_val: Any, **kwargs: Any) -> AsyncIterator[Any]:
        if not self.steps:
            return
        current = input_val
        for i, step in enumerate(self.steps[:-1]):
            if i == 0 and kwargs:
                current = await step.ainvoke(current, **kwargs)
            else:
                current = await step.ainvoke(current)
        last_step = self.steps[-1]
        async for chunk in last_step.astream(current):
            yield chunk

    def __repr__(self) -> str:
        return f"RunnableSequence({' | '.join(repr(s) for s in self.steps)})"

# Extend PromptTemplate and ChatPromptTemplate to behave as Runnables
def _prompt_template_invoke(self: PromptTemplate, input_val: Any, **kwargs: Any) -> str:
    if isinstance(input_val, dict):
        return self.format(**{**input_val, **kwargs})
    elif isinstance(input_val, str) and len(self.input_variables) == 1:
        return self.format(**{self.input_variables[0]: input_val, **kwargs})
    return self.format(**kwargs)

def _chat_prompt_template_invoke(self: ChatPromptTemplate, input_val: Any, **kwargs: Any) -> List[Message]:
    if isinstance(input_val, dict):
        return self.format_messages(**{**input_val, **kwargs})
    elif isinstance(input_val, str) and len(self.input_variables) == 1:
        return self.format_messages(**{self.input_variables[0]: input_val, **kwargs})
    return self.format_messages(**kwargs)

# Mixin Runnable into prompt classes
PromptTemplate.invoke = _prompt_template_invoke  # type: ignore
PromptTemplate.ainvoke = Runnable.ainvoke  # type: ignore
PromptTemplate.stream = Runnable.stream  # type: ignore
PromptTemplate.astream = Runnable.astream  # type: ignore
PromptTemplate.pipe = Runnable.pipe  # type: ignore
PromptTemplate.__or__ = Runnable.__or__  # type: ignore
PromptTemplate.__ror__ = Runnable.__ror__  # type: ignore

ChatPromptTemplate.invoke = _chat_prompt_template_invoke  # type: ignore
ChatPromptTemplate.ainvoke = Runnable.ainvoke  # type: ignore
ChatPromptTemplate.stream = Runnable.stream  # type: ignore
ChatPromptTemplate.astream = Runnable.astream  # type: ignore
ChatPromptTemplate.pipe = Runnable.pipe  # type: ignore
ChatPromptTemplate.__or__ = Runnable.__or__  # type: ignore
ChatPromptTemplate.__ror__ = Runnable.__ror__  # type: ignore

class BaseChatModel(Runnable, abc.ABC):
    """Unified base chat model interface for edge and cloud models."""

    @abc.abstractmethod
    def generate(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> GenerationResult:
        """Generates a response from the model synchronously."""
        pass

    @abc.abstractmethod
    async def agenerate(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> GenerationResult:
        """Generates a response from the model asynchronously."""
        pass

    @abc.abstractmethod
    def stream(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> Iterator[StreamChunk]:
        """Streams response chunks synchronously."""
        pass

    @abc.abstractmethod
    async def astream(self, messages: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> AsyncIterator[StreamChunk]:
        """Streams response chunks asynchronously."""
        pass

    def invoke(self, input_val: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> AIMessage:
        res = self.generate(input_val, **kwargs)
        return res.message

    async def ainvoke(self, input_val: Union[str, Sequence[Union[Message, Dict[str, Any]]]], **kwargs: Any) -> AIMessage:
        res = await self.agenerate(input_val, **kwargs)
        return res.message