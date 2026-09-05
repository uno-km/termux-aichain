"""
Unit tests for termux_aichain.core.base (Runnable, Pipe, Sequence)
"""
import pytest
import asyncio
from termux_aichain.core.base import Runnable, RunnableLambda, RunnableSequence
from termux_aichain.core.prompt import PromptTemplate
from termux_aichain.core.parsers import StringOutputParser

def test_runnable_pipe_operator():
    step1 = RunnableLambda(lambda x: f"hello {x}")
    step2 = RunnableLambda(lambda x: x.upper())
    step3 = RunnableLambda(lambda x: f"[{x}]")
    
    chain = step1 | step2 | step3
    assert isinstance(chain, RunnableSequence)
    assert len(chain.steps) == 3
    
    result = chain.invoke("world")
    assert result == "[HELLO WORLD]"

def test_runnable_pipe_with_prompt_and_callable():
    prompt = PromptTemplate.from_template("Analyze: {text}")
    cleaner = lambda x: x.strip().replace("Analyze: ", "")
    formatter = lambda x: f"Result: {x.title()}"
    
    chain = prompt | cleaner | formatter
    res = chain.invoke({"text": "termux mobile edge"})
    assert res == "Result: Termux Mobile Edge"

@pytest.mark.asyncio
async def test_async_runnable_chain():
    async def async_fetch(val: str) -> str:
        await asyncio.sleep(0.01)
        return f"Async: {val}"
    
    step1 = RunnableLambda(lambda x: f"Init({x})")
    step2 = RunnableLambda(async_fetch)
    
    chain = step1 | step2
    res = await chain.ainvoke("Edge")
    assert res == "Async: Init(Edge)"