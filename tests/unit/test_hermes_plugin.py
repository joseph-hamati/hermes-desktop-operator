from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any


def load_plugin_client() -> ModuleType:
    path = Path(__file__).parents[2] / "hermes-plugin" / "client.py"
    spec = importlib.util.spec_from_file_location("hermes_plugin_client", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"task_id": "task-123"}).encode()


def test_plugin_request_uses_local_url_and_bearer_token(monkeypatch) -> None:
    client = load_plugin_client()
    captured: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("HERMES_OPERATOR_API_TOKEN", "test-token")
    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)

    result = client.request("POST", "/tasks", {"instruction": "Open Notepad"})

    assert result == {"task_id": "task-123"}
    assert captured["request"].full_url == "http://127.0.0.1:8765/tasks"
    assert captured["request"].headers["Authorization"] == "Bearer test-token"
    assert captured["timeout"] == 30
