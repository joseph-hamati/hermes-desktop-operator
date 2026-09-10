from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from desktop_operator.actions.models import Action, ActionRecord

TaskStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]


class TaskCreate(BaseModel):
    instruction: str | None = Field(default=None, min_length=1)
    actions: list[Action] | None = None
    dry_run: bool | None = None
    approvals: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def instruction_or_actions(self) -> TaskCreate:
        if not self.instruction and not self.actions:
            raise ValueError("task requires instruction or actions")
        return self


class TaskSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    status: TaskStatus = "queued"
    instruction: str | None = None
    actions: list[ActionRecord] = Field(default_factory=list)
    current_action: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    errors: list[str] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)
