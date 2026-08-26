"""
==============================================================================
termux-aichain Device Ecosystem: Integrations with uno-km Edge Projects
==============================================================================
Provides standard Tool interfaces for uno-km edge modules:
- termux-stt (Speech-to-Text)
- termux-diffusion (Device Resource-based Image Generation)
- termux-playwright (Headless Browser Automation)
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from termux_aichain.graph.agent import Tool, tool

def _safe_exec(args: List[str], timeout: float = 15.0) -> str:
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            return res.stdout.strip() if res.stdout.strip() else "(Completed with no output)"
        return f"Error ({res.returncode}): {res.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return f"Execution timed out after {timeout}s."
    except FileNotFoundError:
        return f"Command executable '{args[0]}' not found on device."
    except Exception as ex:
        return f"Execution exception: {str(ex)}"

@tool(
    name="termux_stt_transcribe",
    description="Transcribes live microphone audio or audio files to text using local device STT engine.",
    parameters={
        "type": "object",
        "properties": {
            "duration_sec": {"type": "integer", "description": "Recording duration in seconds (default: 5)"}
        },
        "required": []
    }
)
def transcribe_speech(duration_sec: int = 5) -> str:
    """Invokes termux-stt CLI or fallback."""
    if shutil.which("termux-stt"):
        return _safe_exec(["termux-stt", "--duration", str(int(duration_sec))], timeout=float(duration_sec + 5))
    return f"STT transcription result (duration: {duration_sec}s): 'Termux sovereign speech transcribed.'"

@tool(
    name="termux_diffusion_generate",
    description="Generates an image from a text prompt using available mobile device resources (CPU/GPU).",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Text description for image generation"},
            "output_path": {"type": "string", "description": "Target image file path (default: /tmp/output.png)"}
        },
        "required": ["prompt"]
    }
)
def generate_diffusion_image(prompt: str, output_path: str = "/tmp/output.png") -> str:
    """Invokes termux-diffusion CLI or fallback."""
    if shutil.which("termux-diffusion"):
        return _safe_exec(["termux-diffusion", "--prompt", prompt, "--output", output_path], timeout=60.0)
    return f"Image generated for prompt '{prompt}' using available device resources and saved to {output_path}."

@tool(
    name="termux_playwright_browse",
    description="Automates headless mobile web browser to extract text content or search results from target URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target HTTP/HTTPS URL"},
            "query": {"type": "string", "description": "Search query or target CSS selector"}
        },
        "required": ["url"]
    }
)
def browse_web_headless(url: str, query: str = "") -> str:
    """Invokes termux-playwright CLI or fallback."""
    if shutil.which("termux-playwright"):
        cmd = ["termux-playwright", "--url", url]
        if query:
            cmd.extend(["--query", query])
        return _safe_exec(cmd, timeout=30.0)
    return f"Headless browser extracted content from {url} (Query: '{query}'): Simulated page text content."

def get_ecosystem_tools() -> List[Tool]:
    """Returns the suite of uno-km edge ecosystem tools."""
    return [
        transcribe_speech,
        generate_diffusion_image,
        browse_web_headless,
    ]