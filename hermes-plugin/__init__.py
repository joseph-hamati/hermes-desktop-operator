from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .client import cancel_task, get_task, submit_actions, submit_instruction


def _result(handler: Callable[[], dict[str, Any]]) -> str:
    try:
        return json.dumps({"success": True, "task": handler()})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def register(ctx: Any) -> None:
    ctx.register_tool(
        name="desktop_browser_navigate",
        toolset="desktop_operator",
        schema={
            "name": "desktop_browser_navigate",
            "description": (
                "Reliably open Google Chrome's Default profile, focus the address bar, type text "
                "or a URL, and optionally press Enter. This does not switch accounts or sign in."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Search text or URL to enter in Chrome's address bar.",
                    },
                    "press_enter": {
                        "type": "boolean",
                        "description": "Whether to submit the entered text.",
                        "default": True,
                    },
                },
                "required": ["text"],
            },
        },
        handler=lambda params, **kwargs: _result(
            lambda: submit_actions(
                [
                    {
                        "type": "launch_program",
                        "program": "chrome.exe",
                        "args": ["--profile-directory=Default"],
                        "timeout": 15,
                    },
                    {"type": "focus_window", "title_contains": "Chrome", "timeout": 15},
                    {"type": "hotkey", "keys": ["ctrl", "l"], "timeout": 5},
                    {"type": "type_text", "text": params["text"], "timeout": 10},
                    *(
                        [{"type": "press_key", "key": "enter", "timeout": 5}]
                        if params.get("press_enter", True)
                        else []
                    ),
                ]
            )
        ),
    )
    ctx.register_tool(
        name="desktop_operator",
        toolset="desktop_operator",
        schema={
            "name": "desktop_operator",
            "description": (
                "Pass the user's complete natural-language desktop request to the local Windows "
                "operator and return its result. Do not translate the request into action syntax "
                "or split one request across calls. Use only when the user explicitly asks to "
                "control desktop applications."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "The user's complete desktop request, preserved as written.",
                    },
                    "wait_seconds": {
                        "type": "number",
                        "description": "How long to wait for completion, from 0 to 120 seconds.",
                        "minimum": 0,
                        "maximum": 120,
                        "default": 60,
                    },
                },
                "required": ["instruction"],
            },
        },
        handler=lambda params, **kwargs: _result(
            lambda: submit_instruction(
                params["instruction"],
                float(params.get("wait_seconds", 60)),
            )
        ),
    )
    ctx.register_tool(
        name="desktop_task_status",
        toolset="desktop_operator",
        schema={
            "name": "desktop_task_status",
            "description": "Get the status and action results for a desktop task.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        },
        handler=lambda params, **kwargs: _result(lambda: get_task(params["task_id"])),
    )
    ctx.register_tool(
        name="desktop_task_cancel",
        toolset="desktop_operator",
        schema={
            "name": "desktop_task_cancel",
            "description": "Cancel a queued or running desktop task.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        },
        handler=lambda params, **kwargs: _result(lambda: cancel_task(params["task_id"])),
    )
