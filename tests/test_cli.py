"""
Unit tests for termux_aichain CLI module runtime & execution health
"""
import pytest
import urllib.error
from pathlib import Path

def test_cli_module_imports():
    import termux_aichain.cli
    assert termux_aichain.cli is not None

def test_cmd_status_stopped(capsys, monkeypatch):
    from termux_aichain.cli import cmd_status
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline"))
    )
    cmd_status()
    out = capsys.readouterr().out
    assert "stopped" in out

def test_cmd_stop_with_empty_lock_dir(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    from termux_aichain.cli import cmd_stop
    cmd_stop()
    out = capsys.readouterr().out
    assert "No active managed server" in out

def test_cmd_models_listing(capsys):
    from termux_aichain.cli import cmd_models
    cmd_models()
    out = capsys.readouterr().out
    assert "Verified On-Device GGUF Models" in out
    assert "qwen-2.5-1.5b" in out

def test_cmd_stop_stale_pid_does_not_kill_unrelated_process(tmp_path, monkeypatch, capsys):
    # Lock file with a mismatched startIdentity on a non-existent PID
    lock_dir = tmp_path / "termux-aichain"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "managed_8080.lock"
    lock_file.write_text('{"schemaVersion": 1, "pid": 999999, "startIdentity": "forged-or-old-identity", "executablePath": "/bin/sh"}', encoding="utf-8")

    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    from termux_aichain.cli import cmd_stop
    cmd_stop()
    out = capsys.readouterr().out
    assert "Cleaned stale lock files" in out
    assert not lock_file.exists()

def test_cmd_stop_live_unrelated_process_is_never_killed(tmp_path, monkeypatch, capsys):
    import os
    current_pid = os.getpid()
    lock_dir = tmp_path / "termux-aichain"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "managed_8080.lock"
    # Forge a lock file pointing to the current test runner PID but with a fake/old startIdentity
    lock_file.write_text(f'{{"schemaVersion": 1, "pid": {current_pid}, "startIdentity": "fake-old-time-9999", "executablePath": "/bin/sh"}}', encoding="utf-8")

    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    from termux_aichain.cli import cmd_stop
    cmd_stop()
    out = capsys.readouterr().out
    assert "Cleaned stale lock files" in out
    # Current test runner must still be alive!
    assert os.getpid() == current_pid

def test_download_verified_model_mismatch_raises_and_cleans_tmp(tmp_path, monkeypatch):
    import urllib.request
    import io
    from termux_aichain.cli import download_verified_model, MODELS_REGISTRY

    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path))

    # Fake response with corrupted data (magic header correct, but sha mismatch)
    corrupted_data = b"GGUF_CORRUPTED_MODEL_PAYLOAD_HERE"
    class FakeResp:
        def read(self, size):
            nonlocal corrupted_data
            d = corrupted_data
            corrupted_data = b""
            return d
        def __enter__(self): return self
        def __exit__(self, *args): pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req: FakeResp())

    with pytest.raises(ValueError, match="Model SHA-256 integrity verification failed"):
        download_verified_model("qwen-2.5-1.5b", force=True)

    # Temporary file must be deleted on failure
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0

def test_cmd_run_rejects_incompatible_server(monkeypatch, tmp_path, capsys):
    from termux_aichain.cli import cmd_run
    class FakeHealthResp:
        status = 200
        def read(self, size): return b'{"status":"ok","service":"termux-aichain","protocolVersion":"1.0","model":{"id":"different.gguf"}}'
        def __enter__(self): return self
        def __exit__(self, *args): pass

    class FakeOpener:
        def open(self, *args, **kwargs): return FakeHealthResp()

    monkeypatch.setattr("urllib.request.build_opener", lambda *args: FakeOpener())

    # Create dummy valid GGUF model
    m = tmp_path / "target.gguf"
    m.write_bytes(b"GGUF_TEST_DATA")
    cmd_run(str(m), replace=False)
    out = capsys.readouterr().out
    assert "occupied by an incompatible server" in out