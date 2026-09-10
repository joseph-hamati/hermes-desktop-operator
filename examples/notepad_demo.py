from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv


def demo_path() -> Path:
    return Path.home() / "Desktop" / f"hermes-desktop-operator-demo-{int(time.time())}.txt"


def demo_actions(path: Path) -> list[dict[str, object]]:
    return [
        {"type": "launch_program", "program": "notepad.exe", "timeout": 10},
        {"type": "focus_window", "title_contains": "Untitled", "timeout": 10},
        {"type": "type_text", "text": "My first desktop-agent test.", "timeout": 10},
        {"type": "hotkey", "keys": ["ctrl", "s"], "timeout": 5},
        {"type": "focus_window", "title_contains": "Save As", "timeout": 10},
        {"type": "type_text", "text": str(path), "timeout": 10},
        {"type": "press_key", "key": "enter", "timeout": 10},
        {"type": "verify_file_exists", "path": str(path), "timeout": 10},
    ]


async def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the Notepad guaranteed demo.")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--token",
        default=os.environ.get("HERMES_OPERATOR_API_TOKEN", "change-me-local-token"),
    )
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()

    path = demo_path()
    headers = {"Authorization": f"Bearer {args.token}"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        created = await client.post(f"{args.url}/tasks", json={"actions": demo_actions(path)})
        created.raise_for_status()
        task_id = created.json()["task_id"]
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            task = await client.get(f"{args.url}/tasks/{task_id}")
            task.raise_for_status()
            payload = task.json()
            if payload["status"] in {"succeeded", "failed", "cancelled"}:
                print(json.dumps(payload, indent=2))
                return
            await asyncio.sleep(0.5)
    raise TimeoutError(f"demo did not finish within {args.timeout} seconds")


if __name__ == "__main__":
    asyncio.run(main())
