from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from desktop_operator.actions.models import (
    Action,
    ActionRecord,
    ActionResult,
    ClickAction,
    CreateDirectoryAction,
    DoubleClickAction,
    FocusWindowAction,
    HotkeyAction,
    InspectUIAction,
    LaunchProgramAction,
    MoveMouseAction,
    PressKeyAction,
    ReadActiveWindowAction,
    SaveTextFileAction,
    ScreenshotAction,
    TypeTextAction,
    VerifyFileExistsAction,
    WaitAction,
)
from desktop_operator.actions.task import TaskCreate, TaskSnapshot
from desktop_operator.config import Settings
from desktop_operator.logging.audit import AuditLogger
from desktop_operator.safety.policy import SafetyPolicy
from desktop_operator.storage.json_store import JsonTaskStore
from desktop_operator.windows.controller import DesktopController, create_controller


class TaskRunner:
    def __init__(
        self,
        settings: Settings,
        store: JsonTaskStore,
        audit: AuditLogger,
        controller: DesktopController | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.audit = audit
        self.policy = SafetyPolicy(settings)
        self.controller = controller
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}

    def create_task(self, request: TaskCreate, actions: list[Action]) -> TaskSnapshot:
        records = [
            ActionRecord(
                type=action.type,
                params=action.model_dump(exclude={"type", "timeout"}),
                timeout=action.timeout,
            )
            for action in actions
        ]
        task = TaskSnapshot(instruction=request.instruction, actions=records)
        self.store.save(task)
        return task

    def start(self, task: TaskSnapshot, actions: list[Action], request: TaskCreate) -> None:
        cancel = asyncio.Event()
        self._cancel_events[task.id] = cancel
        self._tasks[task.id] = asyncio.create_task(self._run(task, actions, request, cancel))

    async def cancel(self, task_id: str) -> bool:
        event = self._cancel_events.get(task_id)
        if event:
            event.set()
        running = self._tasks.get(task_id)
        if running:
            task = self.store.load(task_id)
            if task and task.status in {"queued", "running"}:
                task.status = "cancelled"
                task.finished_at = datetime.now(UTC)
                task.summary = "Task cancelled."
                task.touch()
                self.store.save(task)
            running.cancel()
            return True
        task = self.store.load(task_id)
        if task and task.status in {"queued", "running"}:
            task.status = "cancelled"
            task.finished_at = datetime.now(UTC)
            task.touch()
            self.store.save(task)
            return True
        return False

    def cancel_all_running(self) -> int:
        count = 0
        for event in self._cancel_events.values():
            event.set()
            count += 1
        for running in self._tasks.values():
            running.cancel()
        return count

    async def _run(
        self,
        task: TaskSnapshot,
        actions: list[Action],
        request: TaskCreate,
        cancel: asyncio.Event,
    ) -> None:
        dry_run = self.settings.dry_run if request.dry_run is None else request.dry_run
        controller = self.controller or create_controller(dry_run)
        task.status = "running"
        task.started_at = datetime.now(UTC)
        task.touch()
        self.store.save(task)
        self.audit.write("task_started", {"task_id": task.id, "dry_run": dry_run})
        try:
            execution = self._execute_actions(
                task,
                actions,
                request.approvals,
                controller,
                cancel,
                dry_run,
            )
            await asyncio.wait_for(
                execution,
                timeout=self.settings.global_task_timeout_seconds,
            )
            if task.status != "cancelled":
                task.status = "succeeded"
                task.summary = "All actions completed successfully."
        except asyncio.CancelledError:
            task.status = "cancelled"
            task.summary = "Task cancelled."
        except Exception as exc:
            task.status = "failed"
            task.errors.append(str(exc))
            task.summary = f"Task failed: {exc}"
            self.audit.write("task_failed", {"task_id": task.id, "error": str(exc)})
        finally:
            task.current_action = None
            task.finished_at = datetime.now(UTC)
            task.touch()
            self.store.save(task)
            self.audit.write("task_finished", {"task_id": task.id, "status": task.status})
            self._tasks.pop(task.id, None)
            self._cancel_events.pop(task.id, None)

    async def _execute_actions(
        self,
        task: TaskSnapshot,
        actions: list[Action],
        approvals: list[str],
        controller: DesktopController,
        cancel: asyncio.Event,
        dry_run: bool,
    ) -> None:
        for index, action in enumerate(actions):
            if cancel.is_set():
                task.status = "cancelled"
                return
            self.policy.validate_action(action, approvals)
            task.current_action = task.actions[index].id
            task.touch()
            self.store.save(task)
            self.audit.write(
                "action_started",
                {"task_id": task.id, "action_id": task.actions[index].id, "type": action.type},
            )
            result = await asyncio.wait_for(
                self._execute_one(action, controller, dry_run),
                timeout=action.timeout,
            )
            task.actions[index].result = ActionResult(success=True, data=result)
            task.results[task.actions[index].id] = result
            task.touch()
            self.store.save(task)
            self.audit.write(
                "action_finished",
                {
                    "task_id": task.id,
                    "action_id": task.actions[index].id,
                    "type": action.type,
                    "result": result,
                },
            )

    async def _execute_one(
        self, action: Action, controller: DesktopController, dry_run: bool
    ) -> dict[str, Any]:
        if isinstance(action, LaunchProgramAction):
            return await controller.launch_program(action.program, action.args)
        if isinstance(action, FocusWindowAction):
            return await controller.focus_window(action.title_contains, action.timeout)
        if isinstance(action, WaitAction):
            return await controller.wait(action.seconds)
        if isinstance(action, MoveMouseAction):
            return await controller.move_mouse(action)
        if isinstance(action, ClickAction | DoubleClickAction):
            return await controller.click(action)
        if isinstance(action, TypeTextAction):
            return await controller.type_text(action)
        if isinstance(action, PressKeyAction):
            return await controller.press_key(action)
        if isinstance(action, HotkeyAction):
            return await controller.hotkey(action)
        if isinstance(action, ScreenshotAction):
            return await controller.screenshot(action.path)
        if isinstance(action, ReadActiveWindowAction):
            return await controller.read_active_window()
        if isinstance(action, InspectUIAction):
            return await controller.inspect_ui(action.title_contains)
        if isinstance(action, VerifyFileExistsAction):
            target = Path(os.path.expandvars(str(action.path))).expanduser()
            deadline = asyncio.get_running_loop().time() + action.timeout
            while asyncio.get_running_loop().time() < deadline:
                if target.exists():
                    return {"path": str(action.path), "exists": True}
                await asyncio.sleep(0.1)
            raise FileNotFoundError(f"file does not exist: {action.path}")
        if isinstance(action, CreateDirectoryAction):
            if not dry_run:
                Path(action.path).mkdir(parents=True, exist_ok=True)
            return {"path": str(action.path), "created": not dry_run, "dry_run": dry_run}
        if isinstance(action, SaveTextFileAction):
            if not dry_run:
                target = Path(os.path.expandvars(str(action.path))).expanduser()
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(action.content, encoding="utf-8")
            return {
                "path": str(action.path),
                "bytes": len(action.content.encode()),
                "dry_run": dry_run,
            }
        raise ValueError(f"unsupported action type: {action.type}")
