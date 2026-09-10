from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from desktop_operator.api import app as app_module
from desktop_operator.api.app import create_app
from desktop_operator.config import Settings
from desktop_operator.executor.runner import TaskRunner
from desktop_operator.logging.audit import AuditLogger
from desktop_operator.planner.ollama import OllamaPlanner
from desktop_operator.storage.json_store import JsonTaskStore
from desktop_operator.windows.controller import DryRunController


def configure_state(tmp_path: Path) -> None:
    settings = Settings(
        api_token="test-token",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
        audit_log=tmp_path / "audit" / "audit.jsonl",
        allowed_programs=["notepad.exe"],
        allowed_directories=[tmp_path],
        dry_run=True,
        ollama_url="http://127.0.0.1:9",
    )
    settings.ensure_dirs()
    app_module.state.settings = settings
    app_module.state.store = JsonTaskStore(settings.data_dir / "tasks")
    app_module.state.audit = AuditLogger(settings.audit_log)
    app_module.state.runner = TaskRunner(
        settings, app_module.state.store, app_module.state.audit, DryRunController()
    )
    app_module.state.planner = OllamaPlanner(settings)


def test_api_auth_required(tmp_path) -> None:
    configure_state(tmp_path)
    client = TestClient(create_app())
    response = client.post("/tasks", json={"actions": [{"type": "wait", "seconds": 0}]})
    assert response.status_code == 401


def test_home_redirects_to_api_docs(tmp_path) -> None:
    configure_state(tmp_path)
    client = TestClient(create_app(), follow_redirects=False)

    response = client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_api_task_lifecycle(tmp_path) -> None:
    configure_state(tmp_path)
    client = TestClient(create_app())
    headers = {"Authorization": "Bearer test-token"}
    created = client.post(
        "/tasks", json={"actions": [{"type": "wait", "seconds": 0}]}, headers=headers
    )
    assert created.status_code == 202
    task_id = created.json()["task_id"]
    response = client.get(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == task_id


def test_health_reports_ollama_status(tmp_path) -> None:
    configure_state(tmp_path)
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert "ollama" in response.json()
