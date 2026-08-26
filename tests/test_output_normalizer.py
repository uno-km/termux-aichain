from termux_aichain.output.normalizer import OutputParserPolicy
import pytest
from termux_aichain.output.scanner import extract_json_candidates, repair_json_light, try_parse_json
from termux_aichain.output.normalizer import OutputNormalizer, RawModelResponse, ToolCall

def test_scanner_nested_brackets_and_strings():
    text = 'Prefix text {"name": "test", "items": [{"val": 1}, {"val": 2}], "text_with_brace": "foo {bar}"} trailing text'
    candidates = extract_json_candidates(text)
    assert len(candidates) == 1
    parsed, repaired = try_parse_json(candidates[0])
    assert parsed["name"] == "test"
    assert parsed["items"][1]["val"] == 2
    assert parsed["text_with_brace"] == "foo {bar}"

def test_scanner_multiple_candidates():
    text = 'First: {"a": 1} and Second: {"b": 2}'
    candidates = extract_json_candidates(text)
    assert len(candidates) == 2
    assert json_loads(candidates[0])["a"] == 1
    assert json_loads(candidates[1])["b"] == 2

def json_loads(s):
    import json
    return json.loads(s)

def test_repair_single_quotes_and_trailing_commas():
    broken = "{'name': 'vibrate_device', 'arguments': {'duration_ms': 1500,},}"
    parsed, repaired = try_parse_json(broken)
    assert parsed is not None
    assert repaired is True
    assert parsed["name"] == "vibrate_device"
    assert parsed["arguments"]["duration_ms"] == 1500

def test_normalizer_native_tool_call():
    raw = RawModelResponse(
        provider="openai",
        model="gpt-4o",
        text="",
        native_tool_calls=[{"id": "call_1", "function": {"name": "vibrate_device", "arguments": '{"duration_ms": 1000}'}}]
    )
    norm = OutputNormalizer.normalize(raw, registered_tool_names=["vibrate_device"])
    assert norm.type == "tool_call"
    assert norm.parse_method == "native"
    assert norm.tool_calls[0].name == "vibrate_device"
    assert norm.tool_calls[0].arguments["duration_ms"] == 1000

def test_normalizer_xml_wrapper():
    raw = RawModelResponse(
        provider="generic",
        model="qwen",
        text="I will vibrate the device.\n<tool_call>\n{\"name\": \"termux_vibrate\", \"arguments\": {\"duration_ms\": 1500}}\n</tool_call>"
    )
    norm = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert norm.type == "tool_call"
    assert norm.parse_method == "xml_tag"
    assert norm.tool_calls[0].name == "termux_vibrate"
    assert norm.tool_calls[0].arguments["duration_ms"] == 1500

def test_normalizer_react_text_pattern():
    raw = RawModelResponse(
        provider="generic",
        model="llama",
        text="Thought: I need to check battery.\nAction: termux_battery_status\nAction Input: {}"
    )
    norm = OutputNormalizer.normalize(raw, registered_tool_names=["termux_battery_status"], policy=OutputParserPolicy(allow_react_text_tool_calls=True))
    assert norm.type == "tool_call"
    assert norm.parse_method == "react_pattern"
    assert norm.tool_calls[0].name == "termux_battery_status"

def test_normalizer_markdown_bash_fence_not_promoted():
    raw = RawModelResponse(
        provider="generic",
        model="qwen-0.5b",
        text="```bash\ntermux_vibrate -d 1500\n```"
    )
    norm = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert norm.type == "text"
    assert norm.tool_calls == []
    assert any("code_block_excluded_from_tool_parsing" in w for w in norm.warnings)

def test_normalizer_plain_text_zero_overkill():
    raw = RawModelResponse(
        provider="generic",
        model="qwen",
        text="??살춳?紐낅？ 獄쏄퀬苑ｇ뵳??遺얠쎗?? ?袁⑹삺 88%??낅빍??"
    )
    norm = OutputNormalizer.normalize(raw, registered_tool_names=["termux_vibrate"])
    assert norm.type == "text"
    assert norm.content == "??살춳?紐낅？ 獄쏄퀬苑ｇ뵳??遺얠쎗?? ?袁⑹삺 88%??낅빍??"
    assert norm.tool_calls == []