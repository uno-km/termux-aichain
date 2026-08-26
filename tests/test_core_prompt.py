"""
Unit tests for termux_aichain.core.prompt
"""
import pytest
from termux_aichain.core.prompt import PromptTemplate, ChatPromptTemplate
from termux_aichain.core.schema import HumanMessage, SystemMessage, AIMessage

def test_prompt_template_basic():
    template = "Hello {name}, your task is {task}."
    prompt = PromptTemplate.from_template(template)
    
    assert prompt.input_variables == ["name", "task"]
    formatted = prompt.format(name="Termux", task="Inference")
    assert formatted == "Hello Termux, your task is Inference."

def test_prompt_template_partial():
    template = "Model: {model} | Device: {device} | Query: {query}"
    prompt = PromptTemplate.from_template(template).partial(model="BitNet-1.58b", device="Galaxy S20")
    
    assert prompt.input_variables == ["query"]
    formatted = prompt.format(query="Check battery")
    assert formatted == "Model: BitNet-1.58b | Device: Galaxy S20 | Query: Check battery"

def test_prompt_template_missing_var():
    prompt = PromptTemplate.from_template("Hello {name} and {other}")
    with pytest.raises(KeyError):
        prompt.format(name="Uno")

def test_chat_prompt_template():
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI assistant running on {os}."),
        ("user", "My query is {query}")
    ])
    
    assert chat_prompt.input_variables == ["os", "query"]
    messages = chat_prompt.format_messages(os="Termux/Android", query="Get battery status")
    
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert messages[0].content == "You are an AI assistant running on Termux/Android."
    assert isinstance(messages[1], HumanMessage)
    assert messages[1].content == "My query is Get battery status"

def test_prompt_template_as_runnable():
    prompt = PromptTemplate.from_template("Hello {user}")
    out = prompt.invoke({"user": "Tester"})
    assert out == "Hello Tester"