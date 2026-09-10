from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HERMES_OPERATOR_",
        extra="ignore",
    )

    api_token: str = Field(default="change-me-local-token")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8765)
    dry_run: bool = Field(default=False)
    global_task_timeout_seconds: int = Field(default=300, ge=1)
    action_timeout_seconds: int = Field(default=30, ge=1)
    data_dir: Path = Field(default=Path("./data"))
    log_dir: Path = Field(default=Path("./logs"))
    audit_log: Path = Field(default=Path("./audit/audit.jsonl"))
    allowed_programs: list[str] = Field(default_factory=lambda: ["notepad.exe", "calc.exe"])
    allowed_directories: list[Path] = Field(
        default_factory=lambda: [Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))]
    )
    ollama_url: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="llama3.1:8b")
    ollama_timeout_seconds: int = Field(default=45, ge=1)
    ollama_temperature: float = Field(default=0.1, ge=0, le=2)
    emergency_stop_hotkey: str = Field(default="ctrl+alt+shift+q")

    @field_validator("host")
    @classmethod
    def localhost_only(cls, value: str) -> str:
        if value not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("daemon must bind to localhost by default; set only loopback hosts")
        return value

    @field_validator("allowed_programs", mode="before")
    @classmethod
    def parse_programs(cls, value: Any) -> list[str]:
        return [item.lower() for item in _split_csv(value)]

    @field_validator("allowed_directories", mode="before")
    @classmethod
    def parse_directories(cls, value: Any) -> list[Path]:
        return [Path(os.path.expandvars(str(item))).expanduser() for item in _split_csv(value)]

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
