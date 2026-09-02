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

@tool(
    name="termux_tts_synth",
    description="Synthesizes text into high-quality WAV audio file using on-device DSP or ONNX neural vocoder.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text to synthesize into speech"},
            "output_path": {"type": "string", "description": "Target audio WAV output file path (default: /tmp/output.wav)"},
            "lang": {"type": "string", "description": "Language code: 'ko' (Korean) or 'en' (English) (default: ko)"},
            "speed": {"type": "number", "description": "Speech speed multiplier between 0.5 and 2.0 (default: 1.0)"},
            "engine": {"type": "string", "description": "Synthesis engine: 'auto', 'dsp', or 'onnx' (default: auto)"}
        },
        "required": ["text"]
    }
)
def synthesize_speech(
    text: str,
    output_path: str = "/tmp/output.wav",
    lang: str = "ko",
    speed: float = 1.0,
    engine: str = "auto"
) -> str:
    """Invokes termux-tts synth CLI or returns explicit error status."""
    tts_bin = shutil.which("termux-tts")
    if not tts_bin:
        return json.dumps({
            "error": "TERMUX_TTS_NOT_FOUND",
            "message": "termux-tts CLI is not installed in PATH. Install via 'pip install termux-tts' or 'termux-aichain install tts'."
        })

    cmd = [
        tts_bin, "synth",
        "-t", text,
        "-o", output_path,
        "-l", lang,
        "-s", str(float(speed)),
        "-e", engine
    ]
    try:
        return _safe_exec(cmd, timeout=45.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "TTS_SYNTHESIS_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

@tool(
    name="termux_tts_speak",
    description="Speaks text aloud directly through Android native speaker output.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Input text to speak aloud"},
            "lang": {"type": "string", "description": "Language code (e.g. 'ko', 'en') (default: ko)"},
            "stream": {"type": "string", "description": "Audio stream: 'MUSIC', 'NOTIFICATION', or 'ALARM' (default: MUSIC)"}
        },
        "required": ["text"]
    }
)
def speak_text(text: str, lang: str = "ko", stream: str = "MUSIC") -> str:
    """Invokes termux-tts speak CLI or returns explicit error status."""
    tts_bin = shutil.which("termux-tts")
    if not tts_bin:
        return json.dumps({
            "error": "TERMUX_TTS_NOT_FOUND",
            "message": "termux-tts CLI is not installed in PATH. Install via 'pip install termux-tts' or 'termux-aichain install tts'."
        })

    cmd = [tts_bin, "speak", "-t", text, "-l", lang, "-s", stream]
    try:
        return _safe_exec(cmd, timeout=30.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "TTS_SPEAK_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

@tool(
    name="termux_vision_vlm",
    description="Analyzes and describes an image or answers questions about an image using on-device Vision-Language Model (VLM).",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Target image file path (PNG/JPEG)"},
            "prompt": {"type": "string", "description": "Text query or prompt asking about the image (default: 'Describe this image in detail.')"},
            "model": {"type": "string", "description": "Optional model ID (e.g., 'smolvlm-500m-q4') or custom .gguf path"}
        },
        "required": ["image_path"]
    }
)
def analyze_image_vlm(image_path: str, prompt: str = "Describe this image in detail.", model: Optional[str] = None) -> str:
    """Invokes termux-vision vlm CLI or returns explicit error status."""
    vision_bin = shutil.which("termux-vision")
    if not vision_bin:
        return json.dumps({
            "error": "TERMUX_VISION_NOT_FOUND",
            "message": "termux-vision CLI is not installed in PATH. Install via 'pip install termux-vision' or 'termux-aichain install vision'."
        })

    cmd = [vision_bin, "vlm", image_path, "-p", prompt]
    if model:
        cmd.extend(["-m", model])
    try:
        return _safe_exec(cmd, timeout=60.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "VISION_VLM_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

@tool(
    name="termux_vision_detect_face",
    description="Detects faces in an image using on-device Haar cascade detector and extracts the cropped face.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Target input image file path"},
            "output_path": {"type": "string", "description": "Target output file path for cropped face (default: /tmp/face_crop.jpg)"}
        },
        "required": ["image_path"]
    }
)
def detect_faces(image_path: str, output_path: str = "/tmp/face_crop.jpg") -> str:
    """Invokes termux-vision detect-face CLI or returns explicit error status."""
    vision_bin = shutil.which("termux-vision")
    if not vision_bin:
        return json.dumps({
            "error": "TERMUX_VISION_NOT_FOUND",
            "message": "termux-vision CLI is not installed in PATH. Install via 'pip install termux-vision' or 'termux-aichain install vision'."
        })

    cmd = [vision_bin, "detect-face", image_path, "-o", output_path]
    try:
        return _safe_exec(cmd, timeout=30.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "VISION_FACE_DETECT_FAILED",
            "command": " ".join(err.cmd),
            "returncode": err.returncode,
            "stderr": err.stderr,
            "message": str(err)
        })

@tool(
    name="termux_vision_canny",
    description="Applies on-device 5-stage Canny Edge Detection to an image.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {"type": "string", "description": "Target input image file path"},
            "output_path": {"type": "string", "description": "Target output file path for edge image (default: /tmp/edges.png)"},
            "low": {"type": "number", "description": "Low hysteresis threshold (default: 40.0)"},
            "high": {"type": "number", "description": "High hysteresis threshold (default: 120.0)"}
        },
        "required": ["image_path"]
    }
)
def detect_edges_canny(
    image_path: str,
    output_path: str = "/tmp/edges.png",
    low: float = 40.0,
    high: float = 120.0
) -> str:
    """Invokes termux-vision canny CLI or returns explicit error status."""
    vision_bin = shutil.which("termux-vision")
    if not vision_bin:
        return json.dumps({
            "error": "TERMUX_VISION_NOT_FOUND",
            "message": "termux-vision CLI is not installed in PATH. Install via 'pip install termux-vision' or 'termux-aichain install vision'."
        })

    cmd = [vision_bin, "canny", image_path, "-o", output_path, "--low", str(float(low)), "--high", str(float(high))]
    try:
        return _safe_exec(cmd, timeout=30.0)
    except SubprocessExecutionError as err:
        return json.dumps({
            "error": "VISION_CANNY_FAILED",
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
        synthesize_speech,
        speak_text,
        analyze_image_vlm,
        detect_faces,
        detect_edges_canny,
    ]