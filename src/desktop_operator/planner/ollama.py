from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import TypeAdapter, ValidationError

from desktop_operator.actions.models import Action
from desktop_operator.config import Settings

SYSTEM_PROMPT = """You convert user desktop requests into JSON actions for Hermes Desktop Operator.
Return only valid JSON with this exact shape: {"actions":[...]}.
Allowed action types are launch_program, focus_window, wait, move_mouse, click, double_click,
type_text, press_key, hotkey, screenshot, read_active_window, inspect_ui, verify_file_exists,
create_directory, save_text_file.
Never emit Python, PowerShell, shell commands, or generated code.
Never invent successful results. The executor will run actions and observe results.
Do not include destructive actions. File overwrites, purchases, messages, email, security settings,
password changes, installs, financial systems, and authentication systems need explicit approval.
Prefer UI Automation targets over fragile absolute coordinates.
Ask for clarification by returning {"clarification_required":"..."} when required
information is missing.
Stop once the requested goal is complete.
"""


class PlannerError(ValueError):
    pass


class OllamaPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._adapter = TypeAdapter(list[Action])

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.settings.ollama_url}/api/tags")
                return {"available": response.is_success, "status_code": response.status_code}
        except httpx.HTTPError as exc:
            return {"available": False, "error": str(exc)}

    async def plan(self, instruction: str) -> list[Action]:
        payload = {
            "model": self.settings.ollama_model,
            "prompt": f"{SYSTEM_PROMPT}\nUser request: {instruction}",
            "stream": False,
            "format": "json",
            "options": {"temperature": self.settings.ollama_temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.ollama_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PlannerError(f"Ollama unavailable: {exc}") from exc

        try:
            body = response.json()
            raw = body.get("response", "")
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise PlannerError("Ollama returned malformed JSON") from exc

        if "clarification_required" in parsed:
            raise PlannerError(f"clarification required: {parsed['clarification_required']}")
        if not isinstance(parsed, dict) or "actions" not in parsed:
            raise PlannerError("Ollama output must contain an actions array")
        try:
            return self._adapter.validate_python(parsed["actions"])
        except ValidationError as exc:
            raise PlannerError(f"Ollama returned invalid actions: {exc}") from exc
