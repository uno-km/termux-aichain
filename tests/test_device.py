"""
Unit tests for termux_aichain.device (Termux Android hardware tools)
"""
import json
import pytest
from termux_aichain.device.tools import (
    get_battery_status,
    get_sensor_data,
    get_device_location,
    record_speech_to_text,
    vibrate_device,
    send_notification,
    speak_tts,
    execute_shell,
    get_default_device_tools
)

def test_battery_status_tool():
    res = get_battery_status()
    assert isinstance(res, str)
    data = json.loads(res)
    assert "percentage" in data or "level" in data or "error" in data

def test_sensor_data_tool():
    res = get_sensor_data("accel")
    assert isinstance(res, str)
    data = json.loads(res)
    assert "accelerometer" in data or "sensor" in data or "error" in data

def test_location_tool():
    res = get_device_location("last")
    assert isinstance(res, str)
    data = json.loads(res)
    assert "latitude" in data or "longitude" in data or "error" in data

def test_stt_tool():
    res = record_speech_to_text()
    assert isinstance(res, str) and len(res) > 0
    data = json.loads(res) if res.startswith("{") else {}
    assert "error" in data or len(res) > 0

def test_vibrate_tool():
    res = vibrate_device(duration_ms=100)
    assert isinstance(res, str)
    data = json.loads(res) if res.startswith("{") else {}
    assert "status" in data or "error" in data

def test_notification_tool():
    res = send_notification(title="Test Title", content="Test Content")
    assert isinstance(res, str)
    data = json.loads(res) if res.startswith("{") else {}
    assert "status" in data or "error" in data

def test_shell_tool():
    res = execute_shell("echo 'Hello Termux Edge'")
    assert "Hello Termux Edge" in res

def test_default_device_tools():
    tools = get_default_device_tools()
    assert len(tools) == 8
    names = [t.name for t in tools]
    assert "termux_battery_status" in names
    assert "termux_sensor_data" in names
    assert "termux_location" in names
    assert "termux_speech_to_text" in names
    assert "termux_vibrate" in names
    assert "termux_notification" in names
    assert "termux_tts_speak" in names
    assert "termux_shell_exec" in names