from __future__ import annotations

import argparse
import asyncio
from typing import Any

import httpx


class HermesDesktopClient:
    def __init__(self, base_url: str, api_token: str, timeout: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.timeout = timeout

    async def submit_instruction(self, instruction: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.post(
                f"{self.base_url}/tasks",
                json={"instruction": instruction},
            )
            response.raise_for_status()
            return response.json()

    async def submit_actions(self, actions: list[dict[str, Any]]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.post(f"{self.base_url}/tasks", json={"actions": actions})
            response.raise_for_status()
            return response.json()

    async def get_task(self, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.get(f"{self.base_url}/tasks/{task_id}")
            response.raise_for_status()
            return response.json()

    async def cancel_task(self, task_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self.headers) as client:
            response = await client.post(f"{self.base_url}/tasks/{task_id}/cancel")
            response.raise_for_status()
            return response.json()


async def _amain() -> None:
    parser = argparse.ArgumentParser(description="Submit a Hermes desktop instruction.")
    parser.add_argument("instruction")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    client = HermesDesktopClient(args.url, args.token)
    print(await client.submit_instruction(args.instruction))


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
