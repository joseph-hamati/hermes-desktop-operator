from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class ActionResult(BaseModel):
    success: bool
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class ActionRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    type: str
    params: dict[str, Any]
    timeout: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    result: ActionResult | None = None


class BaseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    timeout: float = Field(default=30, ge=0.1, le=300)


class LaunchProgramAction(BaseAction):
    type: Literal["launch_program"]
    program: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)


class FocusWindowAction(BaseAction):
    type: Literal["focus_window"]
    title_contains: str = Field(min_length=1)


class WaitAction(BaseAction):
    type: Literal["wait"]
    seconds: float = Field(ge=0, le=300)


class MoveMouseAction(BaseAction):
    type: Literal["move_mouse"]
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    duration: float = Field(default=0, ge=0, le=10)
    coordinate_fallback: bool = True


class _ClickFields(BaseAction):
    x: int | None = Field(default=None, ge=0)
    y: int | None = Field(default=None, ge=0)
    button: Literal["left", "right", "middle"] = "left"
    target_name: str | None = None

    @model_validator(mode="after")
    def target_or_coordinates(self) -> ClickAction:
        if self.target_name is None and (self.x is None or self.y is None):
            raise ValueError("click requires target_name or both x and y")
        return self


class ClickAction(_ClickFields):
    type: Literal["click"]


class DoubleClickAction(_ClickFields):
    type: Literal["double_click"]


class TypeTextAction(BaseAction):
    type: Literal["type_text"]
    text: str
    interval: float = Field(default=0, ge=0, le=1)


class PressKeyAction(BaseAction):
    type: Literal["press_key"]
    key: str = Field(min_length=1, max_length=40)


class HotkeyAction(BaseAction):
    type: Literal["hotkey"]
    keys: list[str] = Field(min_length=2, max_length=5)

    @field_validator("keys")
    @classmethod
    def separate_key_names(cls, value: list[str]) -> list[str]:
        if any("+" in key for key in value):
            raise ValueError("hotkey keys must be separate names such as ['ctrl', 'l']")
        return value


class ScreenshotAction(BaseAction):
    type: Literal["screenshot"]
    path: Path | None = None


class ReadActiveWindowAction(BaseAction):
    type: Literal["read_active_window"]


class InspectUIAction(BaseAction):
    type: Literal["inspect_ui"]
    title_contains: str | None = None


class VerifyFileExistsAction(BaseAction):
    type: Literal["verify_file_exists"]
    path: Path


class CreateDirectoryAction(BaseAction):
    type: Literal["create_directory"]
    path: Path


class SaveTextFileAction(BaseAction):
    type: Literal["save_text_file"]
    path: Path
    content: str
    overwrite: bool = False


Action = Annotated[
    LaunchProgramAction
    | FocusWindowAction
    | WaitAction
    | MoveMouseAction
    | ClickAction
    | DoubleClickAction
    | TypeTextAction
    | PressKeyAction
    | HotkeyAction
    | ScreenshotAction
    | ReadActiveWindowAction
    | InspectUIAction
    | VerifyFileExistsAction
    | CreateDirectoryAction
    | SaveTextFileAction,
    Field(discriminator="type"),
]

ActionAdapter = TypeAdapter(Action)
