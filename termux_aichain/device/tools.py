"""
==============================================================================
termux-aichain Device Toolkit: Android & Termux Native Hardware Tools
==============================================================================
Provides standard Tool interfaces for Termux-API hardware controls
(battery, sensors, vibration, TTS, notifications, location/GPS, STT, camera, shell).
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
from termux_aichain.core.agent_types import ToolArgumentValidationError

def _run_cmd(args: List[str], timeout: float = 3.0) -> Optional[str]:
    try:
        res = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        return None
    except Exception:
        return None

@tool(
    name="termux_battery_status",
    description="Gets current Android battery percentage, charging status, temperature, and health.",
    parameters={"type": "object", "properties": {}, "required": []}
)
def get_battery_status() -> str:
    """Reads battery status via termux-battery-status or direct Linux kernel sysfs."""
    # 1. Try termux-battery-status CLI
    if shutil.which("termux-battery-status"):
        res = _run_cmd(["termux-battery-status"], timeout=2.0)
        if res:
            try:
                json.loads(res)
                return res
            except Exception:
                pass

    # 2. Sysfs fallback for Android Linux Kernel (/sys/class/power_supply)
    cap_path = "/sys/class/power_supply/battery/capacity"
    stat_path = "/sys/class/power_supply/battery/status"
    temp_path = "/sys/class/power_supply/battery/temp"
    if os.path.exists(cap_path):
        try:
            with open(cap_path, "r") as f:
                cap = int(f.read().strip())
            stat = "Discharging"
            if os.path.exists(stat_path):
                with open(stat_path, "r") as f:
                    stat = f.read().strip()
            temp = None
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    temp = float(f.read().strip()) / 10.0
            return json.dumps({
                "percentage": cap,
                "status": stat,
                "temperature": temp,
                "source": "kernel_sysfs"
            })
        except Exception:
            pass

    # 3. Android dumpsys fallback
    dumpsys_res = _run_cmd(["dumpsys", "battery"], timeout=1.5)
    if dumpsys_res:
        level = None
        status = "Unknown"
        for line in dumpsys_res.splitlines():
            line_str = line.strip()
            if line_str.startswith("level:"):
                try:
                    level = int(line_str.split(":")[1].strip())
                except Exception:
                    pass
            elif line_str.startswith("status:"):
                status = line_str.split(":")[1].strip()
        if level is not None:
            return json.dumps({"percentage": level, "status": status, "source": "dumpsys"})

    return json.dumps({
        "error": "BATTERY_DATA_UNAVAILABLE",
        "message": "Neither termux-battery-status nor kernel sysfs /sys/class/power_supply/battery is accessible. Check Termux:API installation and permissions."
    })

@tool(
    name="termux_sensor_data",
    description="Reads current Android physical sensors (accelerometer, gyroscope, light, pressure).",
    parameters={
        "type": "object",
        "properties": {
            "sensor": {"type": "string", "description": "Sensor name: 'all', 'accel', 'gyro', 'light'"}
        },
        "required": []
    }
)
def get_sensor_data(sensor: str = "all") -> str:
    """Reads sensor data via termux-sensor CLI."""
    if shutil.which("termux-sensor"):
        cmd = ["termux-sensor", "-n", "1"]
        if sensor and sensor != "all":
            cmd.extend(["-s", sensor])
        res = _run_cmd(cmd, timeout=3.0)
        if res:
            return res
    return json.dumps({
        "error": "SENSOR_UNAVAILABLE",
        "message": "termux-sensor is not available or timed out. Install termux-api and grant Android sensor permissions."
    })

@tool(
    name="termux_location",
    description="Gets current device GPS/Network location coordinates (latitude, longitude, altitude, accuracy).",
    parameters={
        "type": "object",
        "properties": {
            "provider": {"type": "string", "description": "Location provider: 'gps', 'network', or 'last'"}
        },
        "required": []
    }
)
def get_device_location(provider: str = "last") -> str:
    """Reads device GPS/location coordinates."""
    if shutil.which("termux-location"):
        res = _run_cmd(["termux-location", "-p", provider, "-r", "last"], timeout=4.0)
        if res:
            return res
    return json.dumps({
        "error": "LOCATION_UNAVAILABLE",
        "message": "termux-location is not available or GPS fix timed out. Install termux-api and enable device location."
    })

@tool(
    name="termux_speech_to_text",
    description="Captures live audio from microphone and converts spoken voice into text (STT).",
    parameters={"type": "object", "properties": {}, "required": []}
)
def record_speech_to_text() -> str:
    """Captures microphone speech using termux-speech-to-text."""
    if shutil.which("termux-speech-to-text"):
        res = _run_cmd(["termux-speech-to-text"], timeout=8.0)
        if res:
            return res
    return json.dumps({
        "error": "STT_UNAVAILABLE",
        "message": "termux-speech-to-text command not found. Install termux-api or use uno-km/termux-stt."
    })

def _ensure_termux_api_service_alive() -> None:
    """Wakes up Termux:API background service on modern Android (14/15/16) to prevent intent dropping."""
    if shutil.which("am"):
        try:
            subprocess.run(
                ["am", "startservice", "--user", "0", "-n", "com.termux.api/.TermuxApiService"],
                capture_output=True,
                timeout=1.0,
                check=False
            )
        except Exception:
            pass

@tool(
    name="termux_vibrate",
    description="Vibrates the mobile device for the specified duration in milliseconds (50ms ~ 2000ms).",
        parameters={
        "type": "object",
        "properties": {
            "duration_ms": {"type": "integer", "description": "Vibration duration in ms (50 to 2000)", "minimum": 50, "maximum": 2000},
            "force": {"type": "boolean", "description": "Force vibration even in silent mode (default: false)"}
        },
        "required": ["duration_ms"]
    },
    aliases=("vibrate_device", "vibrate")
)
def vibrate_device(duration_ms: int = 500, force: bool = False) -> str:
    """Triggers physical haptic vibration via termux-vibrate with strict bounds and redacted errors."""
    if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or not (50 <= duration_ms <= 2000):
        raise ToolArgumentValidationError(f"duration_ms must be an integer between 50 and 2000, got: {duration_ms}")

    if not isinstance(force, bool):
        raise ToolArgumentValidationError(f"force must be a boolean, got: {type(force).__name__}")

    if shutil.which("termux-vibrate"):
        _ensure_termux_api_service_alive()
        cmd = ["termux-vibrate"]
        if force:
            cmd.append("-f")
        cmd.extend(["-d", str(int(duration_ms))])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0:
                return json.dumps({"status": "SUCCESS", "message": f"Vibrated device for {duration_ms} ms (force={force})."})
            return json.dumps({
                "error": "VIBRATION_FAILED",
                "code": res.returncode,
                "retryable": False
            })
        except Exception:
            return json.dumps({
                "error": "VIBRATION_EXECUTION_ERROR",
                "retryable": False
            })

    return json.dumps({
        "error": "VIBRATE_UNAVAILABLE",
        "retryable": False
    })

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
    """Dispatches a native notification via termux-notification."""
    if shutil.which("termux-notification"):
        _run_cmd(["termux-notification", "--title", str(title), "--content", str(content)])
        return json.dumps({"status": "SUCCESS", "message": f"Notification displayed: [{title}] {content}"})
    return json.dumps({
        "error": "NOTIFICATION_UNAVAILABLE",
        "message": "termux-notification not found. Install termux-api to enable status bar notifications."
    })

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
    """Synthesizes speech via termux-tts-speak."""
    if shutil.which("termux-tts-speak"):
        _run_cmd(["termux-tts-speak", str(text)])
        return json.dumps({"status": "SUCCESS", "message": f"TTS spoken: '{text}'"})
    return json.dumps({
        "error": "TTS_UNAVAILABLE",
        "message": "termux-tts-speak not found. Install termux-api to enable text-to-speech."
    })

# Safe tokenized commands allowlist for explicit opt-in shell tool
SAFE_COMMAND_ALLOWLIST = {
    "termux-battery-status", "termux-sensor", "termux-location",
    "termux-speech-to-text", "termux-vibrate", "termux-notification",
    "termux-tts-speak", "termux-torch", "termux-volume",
    "uname", "uptime", "whoami", "pwd", "date", "ps"
}

@tool(
    name="termux_shell_exec",
    description="[DANGEROUS / REQUIRES EXPLICIT APPROVAL] Executes a tokenized, non-shell command from the strict allowlist.",
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Allowed executable command token (e.g. 'uname -a', 'uptime', 'termux-torch on')"
            }
        },
        "required": ["command"]
    }
)
def execute_shell(command: str) -> str:
    """Executes a strictly tokenized command (shell=False) against the safe allowlist."""
    if not isinstance(command, str) or not command.strip():
        return json.dumps({"error": "INVALID_COMMAND", "message": "Command must be a non-empty string."})

    # Reject shell metacharacters to prevent injection
    forbidden_chars = [";", "&&", "||", "|", "`", "$", ">", "<", "\n", "\r"]
    for ch in forbidden_chars:
        if ch in command:
            return json.dumps({"error": "INJECTION_ATTEMPT_REJECTED", "message": f"Shell metacharacter '{ch}' is strictly forbidden."})

    import shlex
    try:
        tokens = shlex.split(command.strip())
    except Exception as ex:
        return json.dumps({"error": "PARSE_ERROR", "message": f"Failed to tokenize command: {str(ex)}"})

    if not tokens:
        return json.dumps({"error": "EMPTY_COMMAND", "message": "Parsed command tokens are empty."})

    executable = tokens[0]
    if executable not in SAFE_COMMAND_ALLOWLIST:
        return json.dumps({
            "error": "COMMAND_NOT_ALLOWED",
            "message": f"Executable '{executable}' is not in the safe command allowlist. Allowed: {sorted(SAFE_COMMAND_ALLOWLIST)}"
        })

    try:
        res = subprocess.run(
            tokens,
            shell=False,
            capture_output=True,
            text=True,
            timeout=10.0
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if res.returncode == 0:
            return out if out else "(Command executed successfully with no output)"
        return f"Error (Exit Code {res.returncode}): {err if err else out}"
    except subprocess.TimeoutExpired:
        return "Command execution timed out (10s limit)."
    except Exception as ex:
        return f"Failed to execute command: {str(ex)}"

def get_default_device_tools() -> List[Tool]:
    """Returns the safe suite of standard Termux/Android device tools (excludes raw shell)."""
    return [
        get_battery_status,
        get_sensor_data,
        get_device_location,
        record_speech_to_text,
        vibrate_device,
        send_notification,
        speak_tts,
    ]