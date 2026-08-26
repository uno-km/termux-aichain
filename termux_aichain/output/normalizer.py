"""
==============================================================================
termux-aichain Output Engine: Model Output Normalization & Tool Authorization
==============================================================================
Normalizes raw LLM output, isolates code blocks from tool parsing,
enforces strict tool argument schemas, and rejects repaired JSON execution.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
import html
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from termux_aichain.core.agent_types import ToolCallCandidate, ToolArgumentValidationError
from termux_aichain.output.scanner import extract_json_candidates, try_parse_json, strip_fenced_code_blocks, CodeBlock

@dataclass(frozen=True)
class OutputParserPolicy:
    """Configurable security policy for output normalization and tool promotion."""
    allow_native_tool_calls: bool = True
    allow_json_tool_calls: bool = True
    allow_react_text_tool_calls: bool = False  # P0-2: Default False to prevent example/quote promotion
    allow_json_repair_for_data: bool = True
    allow_json_repair_for_tools: bool = False  # P0-8: Strictly False for hardware tools

@dataclass
class ToolCall:
    """Normalized typed tool call representation."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    repaired: bool = False

@dataclass
class RawModelResponse:
    """Raw unprocessed output payload from any model provider."""
    provider: str
    model: str
    text: str
    native_tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NormalizedModelResponse:
    """Clean normalized output ready for agent loop and tool execution."""
    type: str  # "text", "tool_call", "final", "error"
    content: Optional[str] = None
    tool_calls: List[ToolCall] = field(default_factory=list)
    candidates: List[ToolCallCandidate] = field(default_factory=list)
    finish_reason: Optional[str] = None
    parse_method: str = "raw_text"  # "native", "xml_tag", "balanced_json", "react_pattern", "raw_text"
    repaired: bool = False
    warnings: List[str] = field(default_factory=list)

def validate_tool_arguments(schema: Dict[str, Any], arguments: Dict[str, Any]) -> None:
    """P0-2 & P0-3: Strict zero-dependency JSON Schema argument validator with bounds & enum support."""
    if not schema:
        return

    if schema.get("type") != "object":
        raise ToolArgumentValidationError("Tool schema must define an object type.")

    properties: Dict[str, Any] = schema.get("properties", {})
    required: List[str] = schema.get("required", [])

    # 1. Required fields check
    for field_name in required:
        if field_name not in arguments:
            raise ToolArgumentValidationError(f"Missing required argument: '{field_name}'.")

    # 2. Unknown arguments check (reject additionalProperties unless allowed)
    allow_additional = schema.get("additionalProperties", False)
    if not allow_additional:
        unknown = set(arguments.keys()) - set(properties.keys())
        if unknown:
            raise ToolArgumentValidationError(f"Unknown arguments provided: {', '.join(sorted(unknown))}.")

    # 3. Type, value constraints, bounds, and enum checks
    for name, value in arguments.items():
        if name not in properties:
            continue
        field_schema: Dict[str, Any] = properties[name]
        expected_type = field_schema.get("type")

        if expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ToolArgumentValidationError(f"Argument '{name}' must be an integer, got: {type(value).__name__} ({value}).")
            min_val = field_schema.get("minimum")
            max_val = field_schema.get("maximum")
            if min_val is not None and value < min_val:
                raise ToolArgumentValidationError(f"Argument '{name}' must be >= {min_val}, got: {value}.")
            if max_val is not None and value > max_val:
                raise ToolArgumentValidationError(f"Argument '{name}' must be <= {max_val}, got: {value}.")

        elif expected_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ToolArgumentValidationError(f"Argument '{name}' must be a number, got: {type(value).__name__} ({value}).")
            min_val = field_schema.get("minimum")
            max_val = field_schema.get("maximum")
            if min_val is not None and value < min_val:
                raise ToolArgumentValidationError(f"Argument '{name}' must be >= {min_val}, got: {value}.")
            if max_val is not None and value > max_val:
                raise ToolArgumentValidationError(f"Argument '{name}' must be <= {max_val}, got: {value}.")

        elif expected_type == "boolean":
            if not isinstance(value, bool):
                raise ToolArgumentValidationError(f"Argument '{name}' must be a boolean, got: {type(value).__name__} ({value}).")

        elif expected_type == "string":
            if not isinstance(value, str):
                raise ToolArgumentValidationError(f"Argument '{name}' must be a string, got: {type(value).__name__} ({value}).")
            min_len = field_schema.get("minLength")
            max_len = field_schema.get("maxLength")
            if min_len is not None and len(value) < min_len:
                raise ToolArgumentValidationError(f"Argument '{name}' length must be >= {min_len}.")
            if max_len is not None and len(value) > max_len:
                raise ToolArgumentValidationError(f"Argument '{name}' length must be <= {max_len}.")

        elif expected_type == "array":
            if not isinstance(value, (list, tuple)):
                raise ToolArgumentValidationError(f"Argument '{name}' must be an array, got: {type(value).__name__}.")

        elif expected_type == "object":
            if not isinstance(value, dict):
                raise ToolArgumentValidationError(f"Argument '{name}' must be an object, got: {type(value).__name__}.")

        # Global Enum Check
        if "enum" in field_schema:
            if value not in field_schema["enum"]:
                raise ToolArgumentValidationError(f"Argument '{name}' value '{value}' is not in allowed enum {field_schema['enum']}.")

class OutputNormalizer:
    """Normalizes multi-provider text and JSON variations into standard contracts with fail-closed security."""

    @classmethod
    def normalize(
        cls,
        response: RawModelResponse,
        registered_tool_names: Optional[Sequence[str]] = None,
        policy: Optional[OutputParserPolicy] = None
    ) -> NormalizedModelResponse:
        parser_policy = policy or OutputParserPolicy()
        tools_allowlist: Set[str] = set(registered_tool_names or [])
        warnings: List[str] = []

        # Priority 1: Native Provider Tool Calls
        if parser_policy.allow_native_tool_calls and response.native_tool_calls:
            calls: List[ToolCall] = []
            candidates: List[ToolCallCandidate] = []
            for idx, raw_call in enumerate(response.native_tool_calls):
                fn = raw_call.get("function", {})
                name = fn.get("name") or raw_call.get("name") or ""
                raw_args = fn.get("arguments", {}) or raw_call.get("arguments", {})

                if isinstance(raw_args, str):
                    parsed_args, repaired = try_parse_json(raw_args)
                    args = parsed_args if isinstance(parsed_args, dict) else {}
                elif isinstance(raw_args, dict):
                    args = raw_args
                    repaired = False
                else:
                    args = {}
                    repaired = False

                candidate = ToolCallCandidate(
                    id=raw_call.get("id", f"call_native_{idx}"),
                    name=name,
                    arguments=args,
                    source="native",
                    repaired=repaired
                )
                candidates.append(candidate)

                if not tools_allowlist or name not in tools_allowlist:
                    warnings.append(f"native_unregistered_tool_rejected: '{name}'")
                    continue

                if repaired and not parser_policy.allow_json_repair_for_tools:
                    warnings.append(f"native_repaired_json_tool_call_rejected: '{name}'")
                    continue

                calls.append(ToolCall(id=candidate.id, name=name, arguments=args, repaired=repaired))

            if calls:
                return NormalizedModelResponse(
                    type="tool_call",
                    tool_calls=calls,
                    candidates=candidates,
                    finish_reason=response.finish_reason or "tool_calls",
                    parse_method="native",
                    warnings=warnings
                )

        text = (response.text or "").strip()
        if not text:
            return NormalizedModelResponse(type="text", content="", parse_method="raw_text", warnings=warnings)

        cleaned_text = html.unescape(text)

        # P0-1: Completely isolate fenced code blocks from tool parsing
        tool_candidate_text, code_blocks = strip_fenced_code_blocks(cleaned_text)
        for block in code_blocks:
            if block.language in {"bash", "sh", "shell", "powershell", "cmd", "zsh", "python", "javascript", "typescript", "json"}:
                warnings.append(f"code_block_excluded_from_tool_parsing: {block.language}")

        # P0-2: Fail-closed if allowlist is empty
        if not tools_allowlist:
            return NormalizedModelResponse(
                type="text",
                content=cleaned_text,
                parse_method="raw_text",
                warnings=warnings + ["no_registered_tools_fail_closed"]
            )

        # Priority 2: XML Tool Call Wrapper (<tool_call> ... </tool_call>) from tool_candidate_text ONLY
        xml_match = re.search(r"<tool_call>\s*(.*?)\s*</tool_call>", tool_candidate_text, re.DOTALL)
        if xml_match:
            cand = xml_match.group(1).strip()
            parsed, repaired = try_parse_json(cand)
            if isinstance(parsed, dict):
                name = str(parsed.get("name") or parsed.get("tool") or parsed.get("action") or "")
                raw_args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or {}
                if name in tools_allowlist:
                    if repaired and not parser_policy.allow_json_repair_for_tools:
                        warnings.append(f"xml_repaired_json_rejected: '{name}'")
                    else:
                        return NormalizedModelResponse(
                            type="tool_call",
                            tool_calls=[ToolCall(id="call_xml_0", name=name, arguments=raw_args if isinstance(raw_args, dict) else {}, repaired=repaired)],
                            parse_method="xml_tag",
                            repaired=repaired,
                            warnings=warnings
                        )

        # Priority 3: ReAct Text Pattern (Action: <tool> \n Action Input: <json>)
        if parser_policy.allow_react_text_tool_calls:
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_-]+)", tool_candidate_text)
            if action_match:
                fn_name = action_match.group(1).strip()
                if fn_name in tools_allowlist:
                    after_action = tool_candidate_text[action_match.end():]
                    input_candidates = extract_json_candidates(after_action)
                    if input_candidates:
                        parsed_args, repaired = try_parse_json(input_candidates[0])
                        if isinstance(parsed_args, dict):
                            if not (repaired and not parser_policy.allow_json_repair_for_tools):
                                return NormalizedModelResponse(
                                    type="tool_call",
                                    tool_calls=[ToolCall(id="call_react_0", name=fn_name, arguments=parsed_args, repaired=repaired)],
                                    parse_method="react_pattern",
                                    repaired=repaired,
                                    warnings=warnings
                                )

        # Priority 4: Balanced JSON Candidate Scanner on tool_candidate_text ONLY
        if parser_policy.allow_json_tool_calls:
            candidates = extract_json_candidates(tool_candidate_text)
            if candidates:
                for cand in reversed(candidates):
                    parsed, repaired = try_parse_json(cand)
                    if isinstance(parsed, dict):
                        name = str(parsed.get("name") or parsed.get("tool") or parsed.get("action") or "")
                        if name in tools_allowlist:
                            if repaired and not parser_policy.allow_json_repair_for_tools:
                                warnings.append(f"json_repaired_rejected: '{name}'")
                                continue
                            raw_args = parsed.get("arguments") or parsed.get("args") or parsed.get("parameters") or {}
                            return NormalizedModelResponse(
                                type="tool_call",
                                tool_calls=[ToolCall(id="call_json_0", name=name, arguments=raw_args if isinstance(raw_args, dict) else {}, repaired=repaired)],
                                parse_method="balanced_json",
                                repaired=repaired,
                                warnings=warnings
                            )

        # Priority 5: Standard Natural Language Plain Text
        return NormalizedModelResponse(
            type="text",
            content=cleaned_text,
            parse_method="raw_text",
            warnings=warnings
        )