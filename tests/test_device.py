"""
Unit tests for termux_aichain.device (Termux Android hardware tools)
"""
import json
import pytest
from termux_aichain.device.tools import (
    get_battery_status,
    vibrate_device,
    send_notification,
    speak_tts,
    execute_shell,
    get_default_device_tools
)

def test_battery_status_tool():
    res = get_battery_status()
    assert isinstance(res, str)
    # Must be valid JSON representation
    data = json.loads(res)
    assert "percentage" in data or "level" in data or "status" in data

def test_vibrate_tool():
    res = vibrate_device(duration_ms=100)
    assert isinstance(res, str)

def test_notification_tool():
    res = send_notification(title="Test Title", content="Test Content")
    assert isinstance(res, str)

def test_shell_tool():
    res = execute_shell("echo 'Hello Termux Edge'")
    assert "Hello Termux Edge" in res

def test_default_device_tools():
    tools = get_default_device_tools()
    assert len(tools) == 5
    names = [t.name for t in tools]
    assert "termux_battery_status" in names
    assert "termux_vibrate" in names
    assert "termux_notification" in names
    assert "termux_tts_speak" in names
    assert "termux_shell_exec" in names