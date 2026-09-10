from __future__ import annotations

from desktop_operator.actions.task import TaskSnapshot
from desktop_operator.storage.json_store import JsonTaskStore


def test_task_persistence_roundtrip(tmp_path) -> None:
    store = JsonTaskStore(tmp_path)
    task = TaskSnapshot(summary="stored")
    store.save(task)
    loaded = store.load(task.id)
    assert loaded is not None
    assert loaded.id == task.id
    assert loaded.summary == "stored"
    assert task.id in store.list_ids()
