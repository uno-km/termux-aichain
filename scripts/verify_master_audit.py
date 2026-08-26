#!/usr/bin/env python3
"""
==============================================================================
termux-aichain Master Audit Verifier (scripts/verify_master_audit.py)
==============================================================================
Verifies that termux_aichain_full_source_report.md is byte-for-byte consistent
with the current repository files and SHA-256 manifests.
"""

from __future__ import annotations
import os
import sys
import re
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def compute_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def verify_report() -> bool:
    report_path = REPO_ROOT / "termux_aichain_full_source_report.md"
    if not report_path.exists():
        print(f"[-] FATAL: {report_path} does not exist.")
        return False

    report_content = report_path.read_text(encoding="utf-8")
    print(f"[*] Verifying {report_path} ({len(report_content):,} bytes)...")

    # 1. Parse manifest table rows: | index | `path` | size | `sha256` | class |
    pattern = re.compile(r"^\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*[\d,]+\s*\|\s*`([a-f0-9]{64})`\s*\|\s*([^\|]+)\|", re.MULTILINE)
    matches = pattern.findall(report_content)

    if not matches:
        print("[-] FATAL: No manifest table entries found in report.")
        return False

    print(f"[*] Found {len(matches)} manifest entries in report. Validating checksums...")
    mismatches = 0
    missing = 0

    for rel_path, expected_sha, cls_tag in matches:
        file_path = REPO_ROOT / rel_path
        if not file_path.exists():
            print(f"  [-] MISSING FILE: {rel_path}")
            missing += 1
            continue

        actual_sha = compute_file_sha256(file_path)
        if actual_sha.lower() != expected_sha.lower():
            print(f"  [-] SHA-256 MISMATCH: {rel_path} (Expected: {expected_sha[:8]}..., Actual: {actual_sha[:8]}...)")
            mismatches += 1

    if mismatches > 0 or missing > 0:
        print(f"[-] FAILED: {mismatches} mismatches, {missing} missing files.")
        return False

    print(f"[+] SUCCESS: All {len(matches)} manifest entries verified byte-for-byte against disk.")
    return True

if __name__ == "__main__":
    if verify_report():
        sys.exit(0)
    else:
        sys.exit(1)
