"""
==============================================================================
termux-aichain Device Ecosystem: Integrations with uno-km Edge Projects
==============================================================================
Provides standard Tool interfaces for uno-km edge modules:
- termux-stt (Speech-to-Text)
- termux-diffusion (Device Resource-based Image Generation)
- termux-playwright (Headless Browser Automation)
Zero fake simulation strings - 100% Ground Truth native execution & diagnostics.
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from termux_aichain.graph.agent import Tool, tool

def _safe_exec(args: List[str], timeout: float = 15.0) -> Optional[str]:
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        return None
    except Exception:
        return None

@tool(
    name="termux_stt_transcribe",
    description="Transcribes live microphone audio or audio files to text using local device STT engine.",
    parameters={
        "type": "object",
        "properties": {
            "audio_path": {"type": "string", "description": "Optional WAV audio file path (if omitted, captures microphone)"},
            "duration_sec": {"type": "integer", "description": "Recording duration in seconds (default: 5)"}
        },
        "required": []
    }
)
def transcribe_speech(audio_path: Optional[str] = None, duration_sec: int = 5) -> str:
    """Invokes termux-stt CLI or returns explicit error status."""
    stt_bin = shutil.which("termux-stt")
    if not stt_bin:
        return json.dumps({
            "error": "TERMUX_STT_NOT_FOUND",
            "message": "termux-stt CLI is not installed in PATH. Install via 'pip install termux-stt' or clone uno-km/termux-stt."
        })

    cmd = [stt_bin]
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["--input", audio_path])
    else:
        cmd.extend(["--duration", str(int(duration_sec))])
    
    out = _safe_exec(cmd, timeout=float(duration_sec + 15))
    if out:
        return out
    return json.dumps({
        "error": "TRANSCRIPTION_FAILED",
        "message": f"termux-stt executed but failed to generate transcript for target (audio: {audio_path}, duration: {duration_sec}s)."
    })

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
    """Invokes termux-diffusion CLI or returns explicit error status."""
    diff_bin = shutil.which("termux-diffusion")
    if not diff_bin:
        return json.dumps({
            "error": "TERMUX_DIFFUSION_NOT_FOUND",
            "message": "termux-diffusion CLI is not installed in PATH. Install via 'pip install termux-diffusion' or clone uno-km/termux-diffusion."
        })

    out = _safe_exec([diff_bin, "--prompt", prompt, "--output", output_path], timeout=60.0)
    if out:
        return out
    return json.dumps({
        "error": "IMAGE_GENERATION_FAILED",
        "message": f"termux-diffusion failed to synthesize image for prompt '{prompt}'."
    })

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
    """Invokes termux-playwright CLI or returns explicit error status."""
    play_bin = shutil.which("termux-playwright")
    if not play_bin:
        return json.dumps({
            "error": "TERMUX_PLAYWRIGHT_NOT_FOUND",
            "message": "termux-playwright CLI is not installed in PATH. Install via 'pip install termux-playwright' or clone uno-km/termux-playwright."
        })

    cmd = [play_bin, "--url", url]
    if query:
        cmd.extend(["--query", query])
    out = _safe_exec(cmd, timeout=30.0)
    if out:
        return out
    return json.dumps({
        "error": "BROWSE_FAILED",
        "message": f"termux-playwright failed to extract web content from {url}."
    })

def get_ecosystem_tools() -> List[Tool]:
    """Returns the suite of uno-km edge ecosystem tools."""
    return [
        transcribe_speech,
        generate_diffusion_image,
        browse_web_headless,
    ]