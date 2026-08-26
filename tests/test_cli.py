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
    # Lock file with a mismatched startIdentity
    lock_dir = tmp_path / "termux-aichain"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / "managed_8080.lock"
    lock_file.write_text('{"schemaVersion": 1, "pid": 999999, "startIdentity": "forged-or-old-identity"}', encoding="utf-8")

    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    from termux_aichain.cli import cmd_stop
    cmd_stop()
    out = capsys.readouterr().out
    assert "Cleaned stale lock files" in out
    assert not lock_file.exists()