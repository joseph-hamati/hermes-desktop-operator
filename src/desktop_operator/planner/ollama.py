from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

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
For wait use seconds. For click use target_name or both x and y.
For inspect_ui use only title_contains. To focus a browser address bar use hotkey ctrl+l.
Hotkey keys must be separate names, for example {"type":"hotkey","keys":["ctrl","l"]}.
Type text after focusing a field, then use a separate press_key action for Enter.
Ask for clarification by returning {"clarification_required":"..."} when required
information is missing.
Stop once the requested goal is complete.
"""


class PlanResponse(BaseModel):
    actions: list[Action] = Field(default_factory=list)
    clarification_required: str | None = None


class PlannerError(ValueError):
    pass


class OllamaPlanner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.settings.ollama_url}/api/tags")
                return {"available": response.is_success, "status_code": response.status_code}
        except httpx.HTTPError as exc:
            return {"available": False, "error": str(exc)}

    async def plan(self, instruction: str) -> list[Action]:
        allowed_programs = ", ".join(self.settings.allowed_programs)
        payload = {
            "model": self.settings.ollama_model,
            "prompt": (
                f"{SYSTEM_PROMPT}\n"
                f"Allowed launch_program values: {allowed_programs}. "
                "Use these exact executable names.\n"
                f"User request: {instruction}"
            ),
            "stream": False,
            "format": PlanResponse.model_json_schema(),
            "options": {"temperature": self.settings.ollama_temperature},
        }
        parsed: PlanResponse | None = None
        validation_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.ollama_timeout_seconds
                ) as client:
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
                parsed = PlanResponse.model_validate_json(raw)
                break
            except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
                validation_error = exc
                if attempt == 0:
                    payload["prompt"] += (
                        "\nYour previous response failed schema validation. Correct these errors "
                        f"and return the full JSON again:\n{str(exc)[:2000]}"
                    )

        if parsed is None:
            raise PlannerError(
                f"Ollama returned invalid actions after retry: {validation_error}"
            ) from validation_error

        if parsed.clarification_required:
            raise PlannerError(f"clarification required: {parsed.clarification_required}")
        if not parsed.actions:
            raise PlannerError("Ollama output must contain a non-empty actions array")
        return parsed.actions
