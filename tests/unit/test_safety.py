from __future__ import annotations

from pathlib import Path

import pytest

from desktop_operator.actions.models import LaunchProgramAction, SaveTextFileAction
from desktop_operator.config import Settings
from desktop_operator.safety.policy import SafetyError, SafetyPolicy


def test_program_allowlist(settings) -> None:
    policy = SafetyPolicy(settings)
    policy.validate_action(LaunchProgramAction(type="launch_program", program="notepad.exe"), [])
    with pytest.raises(SafetyError, match="allowlist"):
        policy.validate_action(
            LaunchProgramAction(type="launch_program", program="powershell.exe"),
            [],
        )


def test_path_allowlist(settings, tmp_path: Path) -> None:
    policy = SafetyPolicy(settings)
    policy.validate_action(
        SaveTextFileAction(type="save_text_file", path=tmp_path / "ok.txt", content="ok"), []
    )
    with pytest.raises(SafetyError, match="outside allowed"):
        policy.validate_action(
            SaveTextFileAction(
                type="save_text_file",
                path=Path("C:/Windows/nope.txt"),
                content="x",
            ),
            [],
        )


def test_overwrite_requires_approval(settings, tmp_path: Path) -> None:
    target = tmp_path / "exists.txt"
    target.write_text("existing", encoding="utf-8")
    policy = SafetyPolicy(settings)
    action = SaveTextFileAction(type="save_text_file", path=target, content="new", overwrite=True)
    with pytest.raises(SafetyError, match="approval"):
        policy.validate_action(action, [])
    policy.validate_action(action, ["overwrite_files"])


def test_csv_allowlist_env_parsing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HERMES_OPERATOR_ALLOWED_PROGRAMS", "notepad.exe,calc.exe")
    monkeypatch.setenv("HERMES_OPERATOR_ALLOWED_DIRECTORIES", str(tmp_path))
    parsed = Settings()
    assert parsed.allowed_programs == ["notepad.exe", "calc.exe"]
    assert parsed.allowed_directories == [tmp_path]
