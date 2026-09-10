from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    base_url = os.environ.get("HERMES_OPERATOR_URL", "http://127.0.0.1:8765").rstrip("/")
    token = os.environ.get("HERMES_OPERATOR_API_TOKEN")
    if not token:
        raise RuntimeError("HERMES_OPERATOR_API_TOKEN is not configured in Hermes")

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"desktop operator returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"cannot reach desktop operator at {base_url}; start run_daemon.ps1 first"
        ) from exc


def submit_instruction(instruction: str, wait_seconds: float = 60) -> dict[str, Any]:
    created = request("POST", "/tasks", {"instruction": instruction})
    task_id = created["task_id"]
    deadline = time.monotonic() + wait_seconds

    while time.monotonic() < deadline:
        task = get_task(task_id)
        if task.get("status") in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.5)

    task = get_task(task_id)
    task["polling_timed_out"] = True
    return task


def get_task(task_id: str) -> dict[str, Any]:
    return request("GET", f"/tasks/{task_id}")


def cancel_task(task_id: str) -> dict[str, Any]:
    return request("POST", f"/tasks/{task_id}/cancel")

