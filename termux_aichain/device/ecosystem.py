"""
==============================================================================
termux-aichain Device Ecosystem: Integrations with uno-km Edge Projects
==============================================================================
Provides standard Tool interfaces for uno-km sovereign edge modules:
- termux-bitnet (1.58-bit On-Device LLM)
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

class SubprocessExecutionError(RuntimeError):
    """Raised when an ecosystem CLI tool fails execution with transparent diagnostics."""
    def __init__(self, cmd: List[str], returncode: int, stdout: str, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Command '{' '.join(cmd)}' failed (code {returncode}): {stderr.strip() or stdout.strip()}")


def _safe_exec(args: List[str], timeout: float = 15.0) -> str:
    """Executes ecosystem CLI and returns stdout, raising SubprocessExecutionError with full stderr on failure."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        raise SubprocessExecutionError(args, res.returncode, res.stdout, res.stderr)
    except subprocess.TimeoutExpired as exc:
        raise SubprocessExecutionError(args, -1, "", f"Command timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise SubprocessExecutionError(args, -2, "", f"Executable not found: {exc}") from exc


@tool(
    name="termux_bitnet_infer",
    description="Invokes on-device 1.58-bit BitNet LLM engine for fast local text generation.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Input prompt for BitNet LLM"},
            "max_tokens": {"type": "integer", "description": "Maximum tokens to generate (default: 128)"}
        },
        "required": ["prompt"]
    }
)
def infer_bitnet_llm(prompt: str, max_tokens: int = 128) -> str:
    """Invokes termux-bitnet CLI or returns explicit error status."""
    bitnet_bin = shutil.which("termux-bitnet")
    if not bitnet_bin:
        return json.dumps({
            "error": "TERMUX_BITNET_NOT_FOUND",
            "message": "termux-bitnet CLI is not installed in PATH. Install via 'pip install termux-bitnet' or 'termux-aichain install bitnet'."
        })

    try:
        return _safe_exec([bitnet_bin, "--prompt", prompt, "--n-predict", str(int(max_tokens))], timeout=45.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "BITNET_INFERENCE_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

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
    
    try:
        return _safe_exec(cmd, timeout=float(duration_sec + 15))
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "TRANSCRIPTION_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
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

    try:
        return _safe_exec([diff_bin, "--prompt", prompt, "--output", output_path], timeout=60.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "IMAGE_GENERATION_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
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
    try:
        return _safe_exec(cmd, timeout=30.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "BROWSE_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

def get_ecosystem_tools() -> List[Tool]:
    """Returns the suite of uno-km edge ecosystem tools."""
    return [
        infer_bitnet_llm,
        transcribe_speech,
        generate_diffusion_image,
        browse_web_headless,
    ]