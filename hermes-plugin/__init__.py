from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .client import cancel_task, get_task, submit_instruction


def _result(handler: Callable[[], dict[str, Any]]) -> str:
    try:
        return json.dumps({"success": True, "task": handler()})
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)})


def register(ctx: Any) -> None:
    ctx.register_tool(
        name="desktop_operator",
        toolset="desktop_operator",
        schema={
            "name": "desktop_operator",
            "description": (
                "Execute a natural-language task on the local Windows desktop. "
                "Use only when the user explicitly asks to control desktop applications."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "The desktop task to execute.",
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
