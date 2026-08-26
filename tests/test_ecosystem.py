"""
Unit tests for termux_aichain.device.ecosystem (STT, Diffusion, Playwright edge integrations)
"""
import pytest
from termux_aichain.device.ecosystem import (
    transcribe_speech,
    generate_diffusion_image,
    browse_web_headless,
    get_ecosystem_tools
)

def test_transcribe_speech():
    res = transcribe_speech(duration_sec=2)
    assert isinstance(res, str) and len(res) > 0

def test_generate_diffusion_image():
    res = generate_diffusion_image("A futuristic phone on a desk", output_path="/tmp/test_diff.png")
    assert isinstance(res, str)
    assert "futuristic phone" in res or "saved" in res or "Image" in res

def test_browse_web_headless():
    res = browse_web_headless(url="https://example.com", query="header")
    assert isinstance(res, str)
    assert "example.com" in res or "content" in res

def test_get_ecosystem_tools():
    tools = get_ecosystem_tools()
    assert len(tools) == 3
    names = [t.name for t in tools]
    assert "termux_stt_transcribe" in names
    assert "termux_diffusion_generate" in names
    assert "termux_playwright_browse" in names