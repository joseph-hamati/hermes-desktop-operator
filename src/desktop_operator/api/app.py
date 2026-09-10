from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from desktop_operator.actions.models import Action
from desktop_operator.actions.task import TaskCreate, TaskSnapshot
from desktop_operator.config import Settings
from desktop_operator.executor.runner import TaskRunner
from desktop_operator.logging.audit import AuditLogger
from desktop_operator.planner.ollama import OllamaPlanner
from desktop_operator.storage.json_store import JsonTaskStore
from desktop_operator.windows.emergency import EmergencyStopHotkey


class AppState:
    def __init__(self) -> None:
        self.settings = Settings()
        self.settings.ensure_dirs()
        self.store = JsonTaskStore(self.settings.data_dir / "tasks")
        self.audit = AuditLogger(self.settings.audit_log)
        self.runner = TaskRunner(self.settings, self.store, self.audit)
        self.planner = OllamaPlanner(self.settings)
        self.emergency_stop: EmergencyStopHotkey | None = None


state = AppState()


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = f"Bearer {state.settings.api_token}"
    if authorization != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    state.settings.ensure_dirs()
    if state.emergency_stop is None:
        state.emergency_stop = EmergencyStopHotkey(
            state.settings.emergency_stop_hotkey,
            lambda: state.audit.write(
                "emergency_stop",
                {"cancelled_tasks": state.runner.cancel_all_running()},
            ),
        )
        state.emergency_stop.start()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hermes Desktop Operator",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "host": state.settings.host,
            "dry_run": state.settings.dry_run,
            "ollama": await state.planner.health(),
            "emergency_stop": {
                "hotkey": state.settings.emergency_stop_hotkey,
                "available": state.emergency_stop.available if state.emergency_stop else False,
                "error": state.emergency_stop.error if state.emergency_stop else None,
            },
        }

    @app.post("/tasks", dependencies=[Depends(require_token)], status_code=202)
    async def create_task(request: TaskCreate) -> dict[str, str]:
        try:
            actions: list[Action]
            if request.actions is not None:
                actions = request.actions
            elif request.instruction:
                actions = await state.planner.plan(request.instruction)
            else:
                raise HTTPException(status_code=422, detail="task requires instruction or actions")
            task = state.runner.create_task(request, actions)
            state.runner.start(task, actions, request)
            return {"task_id": task.id}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/tasks/{task_id}", dependencies=[Depends(require_token)])
    async def get_task(task_id: str) -> TaskSnapshot:
        task = state.store.load(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="task not found")
        return task

    @app.post("/tasks/{task_id}/cancel", dependencies=[Depends(require_token)])
    async def cancel_task(task_id: str) -> dict[str, object]:
        cancelled = await state.runner.cancel(task_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail="task not found or already complete")
        return {"task_id": task_id, "cancelled": True}

    return app
