"""
==============================================================================
termux-aichain Device Module Exports
==============================================================================
"""

from termux_aichain.device.tools import (
    get_battery_status,
    get_sensor_data,
    get_device_location,
    record_speech_to_text,
    vibrate_device,
    send_notification,
    speak_tts,
    execute_shell,
    get_default_device_tools,
)

__all__ = [
    "get_battery_status",
    "get_sensor_data",
    "get_device_location",
    "record_speech_to_text",
    "vibrate_device",
    "send_notification",
    "speak_tts",
    "execute_shell",
    "get_default_device_tools",
]