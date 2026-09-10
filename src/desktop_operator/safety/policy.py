from __future__ import annotations

import os
from pathlib import Path

from desktop_operator.actions.models import (
    Action,
    CreateDirectoryAction,
    LaunchProgramAction,
    SaveTextFileAction,
    VerifyFileExistsAction,
)
from desktop_operator.config import Settings


class SafetyError(ValueError):
    pass


class SafetyPolicy:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_action(self, action: Action, approvals: list[str]) -> None:
        if isinstance(action, LaunchProgramAction):
            program = Path(action.program).name.lower()
            executable_name = program if program.endswith(".exe") else f"{program}.exe"
            if (
                program not in self.settings.allowed_programs
                and executable_name not in self.settings.allowed_programs
            ):
                raise SafetyError(f"program '{program}' is not in the allowlist")
        if isinstance(action, CreateDirectoryAction | SaveTextFileAction | VerifyFileExistsAction):
            self._require_allowed_path(action.path)
        if isinstance(action, SaveTextFileAction):
            resolved = self._resolve(action.path)
            if resolved.exists() and not action.overwrite:
                raise SafetyError(f"refusing to overwrite existing file: {resolved}")
            if resolved.exists() and "overwrite_files" not in approvals:
                raise SafetyError("overwriting files requires explicit 'overwrite_files' approval")

    def _require_allowed_path(self, path: Path) -> None:
        resolved = self._resolve(path)
        allowed = [self._resolve(item) for item in self.settings.allowed_directories]
        if not any(resolved == base or base in resolved.parents for base in allowed):
            allowed_text = ", ".join(str(item) for item in allowed)
            raise SafetyError(f"path '{resolved}' is outside allowed directories: {allowed_text}")

    @staticmethod
    def _resolve(path: Path) -> Path:
        expanded = Path(os.path.expandvars(str(path))).expanduser()
        return expanded.resolve(strict=False)
