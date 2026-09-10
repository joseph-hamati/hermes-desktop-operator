from __future__ import annotations

import httpx
import pytest

from desktop_operator.planner.ollama import OllamaPlanner, PlannerError


@pytest.mark.asyncio
async def test_ollama_failure_handling(settings) -> None:
    planner = OllamaPlanner(settings)
    with pytest.raises(PlannerError, match="Ollama unavailable"):
        await planner.plan("open notepad")


@pytest.mark.asyncio
async def test_malformed_model_output(settings, monkeypatch) -> None:
    async def fake_post(self, url, json):  # noqa: ANN001
        return httpx.Response(
            200,
            json={"response": "{not-json"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    planner = OllamaPlanner(settings)
    with pytest.raises(PlannerError, match="malformed JSON"):
        await planner.plan("open notepad")


@pytest.mark.asyncio
async def test_valid_model_output(settings, monkeypatch) -> None:
    captured = {}

    async def fake_post(self, url, json):  # noqa: ANN001
        captured.update(json)
        payload = {"actions": [{"type": "launch_program", "program": "notepad.exe"}]}
        return httpx.Response(
            200,
            json={"response": __import__("json").dumps(payload)},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    planner = OllamaPlanner(settings)
    actions = await planner.plan("open notepad")
    assert actions[0].type == "launch_program"
    assert "Allowed launch_program values: notepad.exe" in captured["prompt"]
