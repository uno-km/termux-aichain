"""
==============================================================================
termux-aichain Device Toolkit: Android & Termux Native Hardware Tools
==============================================================================
Provides standard Tool interfaces for Termux-API hardware controls
(battery, sensors, vibration, TTS, notifications, camera, shell).
Zero external heavy dependencies - Pure Python 3.10+ standard library.
"""

from __future__ import annotations
import os
import json
import shutil
import subprocess
from typing import Any, Dict, List, Optional
from termux_aichain.graph.agent import Tool, tool

def _run_cmd(args: List[str], timeout: float = 3.0) -> str:
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0:
            return res.stdout.strip()
        return f"Error ({res.returncode}): {res.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except FileNotFoundError:
        return f"Command '{args[0]}' not found on this system."
    except Exception as ex:
        return f"Execution error: {str(ex)}"

@tool(
    name="termux_battery_status",
    description="Gets current Android battery percentage, charging status, temperature, and health.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_battery_status() -> str:
    """Reads battery status via termux-battery-status or sysfs fallback."""
    if shutil.which("termux-battery-status"):
        res = _run_cmd(["termux-battery-status"], timeout=3.0)
        if res and not res.startswith("Error"):
            return res

    # Sysfs fallback for Android Linux
    cap_path = "/sys/class/power_supply/battery/capacity"
    stat_path = "/sys/class/power_supply/battery/status"
    if os.path.exists(cap_path):
        try:
            with open(cap_path, "r") as f:
                cap = f.read().strip()
            stat = "Unknown"
            if os.path.exists(stat_path):
                with open(stat_path, "r") as f:
                    stat = f.read().strip()
            return json.dumps({"percentage": int(cap), "status": stat, "source": "sysfs"})
        except Exception:
            pass

    return json.dumps({"percentage": 85, "status": "Simulated", "note": "Non-termux fallback"})

@tool(
    name="termux_vibrate",
    description="Vibrates the mobile device for the specified duration in milliseconds.",
    parameters={
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer", "description": "Vibration duration in ms (e.g. 500)"}
        },
        "required": ["duration_ms"]
    }
)
def vibrate_device(duration_ms: int = 500) -> str:
    if shutil.which("termux-vibrate"):
        return _run_cmd(["termux-vibrate", "-d", str(int(duration_ms))])
    return f"Device simulated vibration for {duration_ms} ms."

@tool(
    name="termux_notification",
    description="Shows a native Android status bar notification with a title and content.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Notification title"},
            "content": {"type": "string", "description": "Notification body content"}
        },
        "required": ["title", "content"]
    }
)
def send_notification(title: str, content: str) -> str:
    if shutil.which("termux-notification"):
        return _run_cmd(["termux-notification", "--title", str(title), "--content", str(content)])
    return f"Simulated Notification: [{title}] {content}"

@tool(
    name="termux_tts_speak",
    description="Speaks the given text out loud using the Android Text-to-Speech (TTS) engine.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to speak out loud"}
        },
        "required": ["text"]
    }
)
def speak_tts(text: str) -> str:
    if shutil.which("termux-tts-speak"):
        return _run_cmd(["termux-tts-speak", str(text)])
    return f"Simulated TTS spoken: '{text}'"

@tool(
    name="termux_shell_exec",
    description="Executes a shell command in the local Termux environment safely.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command line to execute"}
        },
        "required": ["command"]
    }
)
def execute_shell(command: str) -> str:
    try:
        res = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10.0
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if res.returncode == 0:
            return out if out else "(Command executed successfully with no output)"
        return f"Error ({res.returncode}): {err if err else out}"
    except subprocess.TimeoutExpired:
        return "Command execution timed out (10s)."
    except Exception as ex:
        return f"Failed to execute command: {str(ex)}"

def get_default_device_tools() -> List[Tool]:
    """Returns the suite of standard Termux/Android device tools."""
    return [
        get_battery_status,
        vibrate_device,
        send_notification,
        speak_tts,
        execute_shell,
    ]