"""
==============================================================================
termux-aichain: Sovereign Process Identity & Safe Ownership Validator
==============================================================================
Prevents PID reuse attacks and unauthorized process termination.
"""
from __future__ import annotations
import os
import sys
import hmac
import ctypes
from pathlib import Path
from typing import Any, Dict, Optional

def get_process_start_identity(pid: int) -> str:
    """Returns an OS-unique process start identifier (start ticks or creation timestamp)."""
    if pid <= 0:
        return ""

    # 1. Linux & Android Termux ProcFS (/proc/<pid>/stat starttime field)
    proc_stat = Path(f"/proc/{pid}/stat")
    if proc_stat.exists():
        try:
            content = proc_stat.read_text(encoding="utf-8", errors="ignore")
            closing_paren = content.rfind(")")
            if closing_paren != -1:
                fields = content[closing_paren + 1:].strip().split()
                if len(fields) >= 20:
                    return f"linux-ticks-{fields[19]}"
        except Exception:
            pass

    # 2. Windows Kernel32 GetProcessTimes
    if sys.platform == "win32":
        try:
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                try:
                    class FILETIME(ctypes.Structure):
                        _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]
                    creation = FILETIME()
                    exit_time = FILETIME()
                    kernel = FILETIME()
                    user = FILETIME()
                    if kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
                        return f"win-time-{creation.dwHighDateTime}-{creation.dwLowDateTime}"
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass

    return f"generic-pid-{pid}"

def verify_managed_process_ownership(pid: int, lock_meta: Dict[str, Any]) -> bool:
    """Strictly validates that PID matches the recorded startIdentity and executable metadata."""
    if pid <= 0 or not isinstance(lock_meta, dict):
        return False

    expected_identity = lock_meta.get("startIdentity")
    if not expected_identity:
        # Strict fail-closed: missing startIdentity in lock metadata rejects signal sending
        return False

    current_identity = get_process_start_identity(pid)
    if not current_identity or not hmac.compare_digest(current_identity, expected_identity):
        return False

    # Check executable path if present in Linux
    proc_exe = Path(f"/proc/{pid}/exe")
    expected_executable = lock_meta.get("executablePath")
    if proc_exe.exists() and expected_executable:
        try:
            real_target = os.path.realpath(proc_exe)
            real_expected = os.path.realpath(expected_executable)
            if real_target != real_expected and not any(k in real_target for k in ("llama-server", "termux-aichain")):
                return False
        except Exception:
            pass

    return True