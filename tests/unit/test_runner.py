from __future__ import annotations

import asyncio

import pytest

from desktop_operator.actions.models import WaitAction
from desktop_operator.actions.task import TaskCreate
from desktop_operator.executor.runner import TaskRunner
from desktop_operator.logging.audit import AuditLogger
from desktop_operator.storage.json_store import JsonTaskStore
from desktop_operator.windows.controller import DryRunController


class SlowDryRunController(DryRunController):
    async def wait(self, seconds: float) -> dict[str, object]:
        await asyncio.sleep(seconds)
        return {"seconds": seconds}


@pytest.mark.asyncio
async def test_dry_run_behavior(settings, tmp_path) -> None:
    store = JsonTaskStore(tmp_path / "tasks")
    runner = TaskRunner(settings, store, AuditLogger(tmp_path / "audit.jsonl"), DryRunController())
    request = TaskCreate.model_validate({"actions": [{"type": "wait", "seconds": 0}]})
    task = runner.create_task(request, request.actions or [])
    runner.start(task, request.actions or [], request)
    await asyncio.sleep(0.05)
    saved = store.load(task.id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert saved.actions[0].result is not None
    assert saved.actions[0].result.success is True


@pytest.mark.asyncio
async def test_timeout_handling(settings, tmp_path) -> None:
    settings.global_task_timeout_seconds = 1
    store = JsonTaskStore(tmp_path / "tasks")
    runner = TaskRunner(
        settings,
        store,
        AuditLogger(tmp_path / "audit.jsonl"),
        SlowDryRunController(),
    )
    request = TaskCreate(actions=[WaitAction(type="wait", seconds=1, timeout=0.1)])
    task = runner.create_task(request, request.actions or [])
    runner.start(task, request.actions or [], request)
    saved = None
    for _ in range(20):
        await asyncio.sleep(0.02)
        saved = store.load(task.id)
        if saved and saved.status == "failed":
            break
    assert saved is not None
    assert saved.status == "failed"
    assert saved.errors


@pytest.mark.asyncio
async def test_cancellation(settings, tmp_path) -> None:
    store = JsonTaskStore(tmp_path / "tasks")
    runner = TaskRunner(settings, store, AuditLogger(tmp_path / "audit.jsonl"), DryRunController())
    request = TaskCreate(actions=[WaitAction(type="wait", seconds=1, timeout=2)])
    task = runner.create_task(request, request.actions or [])
    runner.start(task, request.actions or [], request)
    assert await runner.cancel(task.id) is True
    await asyncio.sleep(0.05)
    saved = store.load(task.id)
    assert saved is not None
    assert saved.status == "cancelled"
