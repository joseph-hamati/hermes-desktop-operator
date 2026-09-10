from __future__ import annotations

import pytest
from pydantic import ValidationError

from desktop_operator.actions.task import TaskCreate


def test_valid_actions_are_accepted() -> None:
    task = TaskCreate.model_validate(
        {
            "actions": [
                {"type": "launch_program", "program": "notepad.exe"},
                {"type": "type_text", "text": "hello"},
                {"type": "hotkey", "keys": ["ctrl", "s"]},
            ]
        }
    )
    assert task.actions is not None
    assert [action.type for action in task.actions] == ["launch_program", "type_text", "hotkey"]


def test_unknown_action_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"actions": [{"type": "run_shell", "command": "dir"}]})


def test_malformed_click_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"actions": [{"type": "click"}]})


def test_extra_parameters_are_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {"actions": [{"type": "press_key", "key": "enter", "command": "bad"}]}
        )


def test_hotkey_rejects_combined_key_names() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate(
            {"actions": [{"type": "hotkey", "keys": ["ctrl+l", "enter"]}]}
        )
