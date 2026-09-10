from __future__ import annotations

import os
from pathlib import Path

import pytest

from desktop_operator.config import Settings


@pytest.fixture()
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("HERMES_OPERATOR_API_TOKEN", "test-token")
    return Settings(
        api_token="test-token",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        audit_log=tmp_path / "audit" / "audit.jsonl",
        allowed_programs=["notepad.exe"],
        allowed_directories=[tmp_path],
        dry_run=True,
        global_task_timeout_seconds=2,
        action_timeout_seconds=1,
        ollama_url="http://127.0.0.1:9",
    )


@pytest.fixture(autouse=True)
def clean_operator_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("HERMES_OPERATOR_"):
            monkeypatch.delenv(key, raising=False)
