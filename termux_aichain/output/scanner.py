"""
==============================================================================
termux-aichain Output Engine: Balanced JSON Scanner & CodeBlock Separation
==============================================================================
Provides ReDoS-free deterministic bracket-depth JSON extraction and fenced
code block isolation. Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import re
import json
import html
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

@dataclass(frozen=True)
class CodeBlock:
    """Isolated fenced markdown code block."""
    language: str
    content: str

def strip_fenced_code_blocks(text: str) -> Tuple[str, List[CodeBlock]]:
    """P0-1: Completely isolates and strips all fenced code blocks from text.
    
    Ensures JSON or commands inside ```bash, ```python, etc. are never passed
    to subsequent tool parsers or balanced scanners.
    """
    if not text:
        return "", []

    blocks: List[CodeBlock] = []
    pattern = re.compile(r"```([a-zA-Z0-9_+-]*)[ \t]*\r?\n([\s\S]*?)```")

    def replace_match(match: re.Match[str]) -> str:
        lang = match.group(1).strip().lower()
        content = match.group(2)
        blocks.append(CodeBlock(language=lang, content=content))
        return "\n"

    remaining = pattern.sub(replace_match, text)
    return remaining, blocks

def extract_json_candidates(text: str) -> List[str]:
    """Extracts balanced JSON candidates using bracket-depth stack tracking.
    
    Prevents catastrophic backtracking (ReDoS) and safely handles
    nested braces, strings with brackets, and multiple JSON payloads.
    """
    if not text:
        return []

    cleaned = html.unescape(text)

    results: List[str] = []
    start: Optional[int] = None
    stack: List[str] = []
    in_string = False
    escaped = False

    for index, char in enumerate(cleaned):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char in "{[":
            if not stack:
                start = index
            stack.append(char)
            continue

        if char in "}]":
            if not stack:
                continue

            expected = "{" if char == "}" else "["
            if stack[-1] != expected:
                stack.clear()
                start = None
                continue

            stack.pop()

            if not stack and start is not None:
                candidate = cleaned[start:index + 1].strip()
                if candidate:
                    results.append(candidate)
                start = None

    return results

def repair_json_light(raw_json: str) -> str:
    """Pure-Python best-effort display/data repair. NOT suitable for executable tool calls."""
    s = raw_json.strip()
    if not s:
        return "{}"

    if "'" in s and '"' not in s:
        s = s.replace("'", '"')

    s = re.sub(r",\s*([}\]])", r"\1", s)
    s = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', s)

    return s

def try_parse_json(candidate: str) -> Tuple[Optional[Any], bool]:
    """Attempts standard json.loads, falling back to light display repair.

    반환: (parsed_value, was_repaired)
    파싱 실패 시: (None, False) — 예상 밖 예외(MemoryError 등)는 재발생.
    """
    try:
        return json.loads(candidate), False
    except json.JSONDecodeError:
        pass  # Allowed: try repair path below. Final failure -> (None, False).
    except (TypeError, ValueError) as _json_err:
        # json.loads가 str 외 타입을 받거나 surrogate 등 — 파싱 불가로 처리
        return None, False

    try:
        repaired = repair_json_light(candidate)
        return json.loads(repaired), True
    except json.JSONDecodeError:
        return None, False
    except (TypeError, ValueError):
        return None, False
    # MemoryError, SystemError 등 예상 밖 예외는 의도적으로 재발생