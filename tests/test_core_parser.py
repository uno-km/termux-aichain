"""
Unit tests for termux_aichain.core.parsers
"""
import pytest
from termux_aichain.core.parsers import StringOutputParser, JsonOutputParser, RegexOutputParser
from termux_aichain.core.schema import AIMessage, GenerationResult

def test_string_output_parser():
    parser = StringOutputParser(strip=True)
    msg = AIMessage(content="   Termux Edge Agent   \n")
    assert parser.invoke(msg) == "Termux Edge Agent"

def test_json_output_parser_markdown():
    parser = JsonOutputParser()
    text = """Here is the structured JSON output:
```json
{
  "device": "Galaxy S20",
  "battery": 85,
  "status": "charging"
}
```
Done!"""
    data = parser.invoke(text)
    assert data["device"] == "Galaxy S20"
    assert data["battery"] == 85
    assert data["status"] == "charging"

def test_json_output_parser_raw_text():
    parser = JsonOutputParser()
    text = 'Some prefix {"key": "value", "items": [1, 2, 3]} some suffix'
    data = parser.invoke(text)
    assert data["key"] == "value"
    assert data["items"] == [1, 2, 3]

def test_json_output_parser_fallback():
    parser = JsonOutputParser(default_factory=lambda: {"status": "fallback"})
    data = parser.invoke("Invalid non-json output")
    assert data == {"status": "fallback"}

def test_regex_output_parser():
    parser = RegexOutputParser(regex=r"Temperature:\s*(\d+\.?\d*)C", group=1)
    res = parser.invoke("The CPU Temperature: 42.5C currently.")
    assert res == "42.5"