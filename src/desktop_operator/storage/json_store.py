from __future__ import annotations

import json
from pathlib import Path

from desktop_operator.actions.task import TaskSnapshot


class JsonTaskStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, task: TaskSnapshot) -> None:
        path = self.root / f"{task.id}.json"
        path.write_text(task.model_dump_json(indent=2), encoding="utf-8")

    def load(self, task_id: str) -> TaskSnapshot | None:
        path = self.root / f"{task_id}.json"
        if not path.exists():
            return None
        return TaskSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_ids(self) -> list[str]:
        return [path.stem for path in self.root.glob("*.json")]
