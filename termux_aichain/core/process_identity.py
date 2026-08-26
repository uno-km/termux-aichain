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

    # 3. Fallback: Fail-closed (do NOT return generic PID)
    return ""

def verify_managed_process_ownership(pid: int, lock_meta: Dict[str, Any]) -> bool:
    """Strictly validates that PID matches the recorded startIdentity, schemaVersion, and executable metadata."""
    if pid <= 0 or not isinstance(lock_meta, dict):
        return False

    # P0-5: Validate schemaVersion and required fields
    if lock_meta.get("schemaVersion") != 1:
        return False

    required_fields = {"schemaVersion", "pid", "startIdentity", "executablePath"}
    if not required_fields.issubset(lock_meta.keys()):
        return False

    if lock_meta.get("pid") != pid:
        return False

    expected_identity = str(lock_meta.get("startIdentity", ""))
    if not expected_identity:
        return False

    current_identity = get_process_start_identity(pid)
    if not current_identity or not hmac.compare_digest(current_identity, expected_identity):
        return False

    # P0-4: Strict realpath comparison on Linux (zero substring matching)
    proc_exe = Path(f"/proc/{pid}/exe")
    expected_executable = str(lock_meta.get("executablePath", ""))
    if proc_exe.exists():
        if not expected_executable:
            return False
        try:
            real_target = os.path.normcase(os.path.realpath(proc_exe))
            real_expected = os.path.normcase(os.path.realpath(expected_executable))
            if not hmac.compare_digest(real_target, real_expected):
                return False
        except Exception:
            return False

    return True