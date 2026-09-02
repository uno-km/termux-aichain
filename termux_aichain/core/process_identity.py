"""
==============================================================================
termux-aichain: Sovereign Process Identity & Safe Ownership Validator
==============================================================================
Prevents PID reuse attacks and unauthorized process termination.

Exception handling policy:
  - PermissionError: access denied — identity CANNOT be read, not same as "not alive"
  - FileNotFoundError / ProcessLookupError: process gone — fail-closed
  - OSError: I/O or platform error — fail-closed with log
  - Other unexpected exceptions are re-raised (do not swallow)
"""
from __future__ import annotations
import logging
import os
import sys
import hmac
import ctypes
from pathlib import Path
from typing import Any, Dict, Optional

_logger = logging.getLogger("termux_aichain.core.process_identity")


def get_process_start_identity(pid: int) -> str:
    """Returns an OS-unique process start identifier (start ticks or creation timestamp).

    Returns "" on all failure paths (fail-closed), but logs the reason so callers
    are not left without diagnostic context.
    """
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
            # stat 파일 파싱 성공이나 starttime 필드 없음 — 형식 이상
            _logger.debug("[process_identity] pid=%d: /proc/stat parsed but starttime field missing", pid)
        except PermissionError as _perm_err:
            # 권한 없음 — process 생존 여부 불명. fail-closed.
            _logger.warning(
                "[process_identity] pid=%d: PermissionError reading /proc/stat: %s", pid, _perm_err
            )
        except FileNotFoundError:
            # 프로세스가 stat 읽기 사이에 종료됨 — fail-closed.
            _logger.debug("[process_identity] pid=%d: /proc/stat vanished (process likely exited)", pid)
        except OSError as _os_err:
            _logger.warning("[process_identity] pid=%d: OSError reading /proc/stat: %s", pid, _os_err)
        # MemoryError, UnicodeDecodeError 등 예상 밖 예외는 재발생

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
                    if kernel32.GetProcessTimes(
                        handle,
                        ctypes.byref(creation), ctypes.byref(exit_time),
                        ctypes.byref(kernel), ctypes.byref(user),
                    ):
                        return f"win-time-{creation.dwHighDateTime}-{creation.dwLowDateTime}"
                    _logger.debug(
                        "[process_identity] pid=%d: GetProcessTimes returned False (process may have exited)", pid
                    )
                finally:
                    kernel32.CloseHandle(handle)
            else:
                _logger.debug("[process_identity] pid=%d: OpenProcess returned null handle", pid)
        except PermissionError as _perm_err:
            _logger.warning(
                "[process_identity] pid=%d: PermissionError via Win32 API: %s", pid, _perm_err
            )
        except OSError as _os_err:
            _logger.warning("[process_identity] pid=%d: OSError via Win32 API: %s", pid, _os_err)
        except AttributeError as _attr_err:
            # ctypes.windll 가용 여부 플랫폼 차이
            _logger.warning("[process_identity] Win32 ctypes unavailable: %s", _attr_err)
        # 예상 밖 예외는 재발생

    # 3. Fallback: Fail-closed (do NOT return generic PID — PID reuse attack vector)
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
        except PermissionError as _perm_err:
            # 실행 파일 경로 검증 불가 — fail-closed (False 반환)
            _logger.warning(
                "[process_identity] pid=%d: PermissionError resolving exe path: %s", pid, _perm_err
            )
            return False
        except (OSError, ValueError) as _os_err:
            _logger.warning("[process_identity] pid=%d: OSError resolving exe path: %s", pid, _os_err)
            return False
        # 예상 밖 예외는 재발생

    return True