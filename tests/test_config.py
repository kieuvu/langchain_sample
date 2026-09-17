import sys

import pytest

import cli
from config import load_settings


def test_missing_settings_are_named(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for name in ("QWEN_BASE_URL", "QWEN_MODEL_NAME", "QWEN_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(RuntimeError, match="QWEN_BASE_URL, QWEN_MODEL_NAME"):
        load_settings()


def test_cli_reports_missing_settings(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QWEN_BASE_URL", raising=False)
    monkeypatch.delenv("QWEN_MODEL_NAME", raising=False)
    monkeypatch.setattr(sys, "argv", ["chat-service", "Hello"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "QWEN_BASE_URL" in capsys.readouterr().err
