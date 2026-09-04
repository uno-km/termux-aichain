"""
Tests for generate_master_audit.py scan_source_manifest:
- Deleted/missing file
- Corrupted encoding (non-UTF-8 binary data in text file)
- Unreadable/permission denied file
- Directory/non-regular file
Verifies that scan_source_manifest does NOT silently pass and reports:
audit_complete = False, failed_files > 0, failures structured list.
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_master_audit import scan_source_manifest


def test_missing_file_fails_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        tracked = ["missing_file.py"]

        manifest, sources, summary = scan_source_manifest(tracked, root)

        assert summary["audit_complete"] is False
        assert summary["failed_files"] == 1
        assert summary["scanned_files"] == 1
        assert len(summary["failures"]) == 1
        assert summary["failures"][0]["error"]["code"] == "AUDIT_FILE_NOT_FOUND"


def test_corrupted_encoding_fails_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        corrupted_file = root / "corrupted.py"
        # Invalid UTF-8 sequence
        corrupted_file.write_bytes(b"\x80\x81\xff\xfe\xfa")

        tracked = ["corrupted.py"]
        manifest, sources, summary = scan_source_manifest(tracked, root)

        assert summary["audit_complete"] is False
        assert summary["failed_files"] == 1
        assert summary["failures"][0]["error"]["code"] == "AUDIT_SOURCE_READ_FAILED"
        assert summary["failures"][0]["error"]["cause_type"] == "UnicodeDecodeError"


def test_unreadable_file_fails_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        f = root / "unreadable.py"
        f.write_text("print('test')", encoding="utf-8")

        tracked = ["unreadable.py"]

        # Simulate PermissionError on read_text
        with patch.object(Path, "read_text", side_effect=PermissionError("Access denied")):
            manifest, sources, summary = scan_source_manifest(tracked, root)

            assert summary["audit_complete"] is False
            assert summary["failed_files"] == 1
            assert summary["failures"][0]["error"]["code"] == "AUDIT_SOURCE_READ_FAILED"
            assert summary["failures"][0]["error"]["cause_type"] == "PermissionError"


def test_non_regular_file_directory_fails_audit():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        sub_dir = root / "a_directory"
        sub_dir.mkdir()

        tracked = ["a_directory"]
        manifest, sources, summary = scan_source_manifest(tracked, root)

        assert summary["audit_complete"] is False
        assert summary["failed_files"] == 1
        assert summary["failures"][0]["error"]["code"] == "AUDIT_NOT_A_REGULAR_FILE"


if __name__ == "__main__":
    test_missing_file_fails_audit()
    print("[PASS] test_missing_file_fails_audit")
    test_corrupted_encoding_fails_audit()
    print("[PASS] test_corrupted_encoding_fails_audit")
    test_unreadable_file_fails_audit()
    print("[PASS] test_unreadable_file_fails_audit")
    test_non_regular_file_directory_fails_audit()
    print("[PASS] test_non_regular_file_directory_fails_audit")
    print("ALL AUDIT SCRIPT TESTS PASSED!")
