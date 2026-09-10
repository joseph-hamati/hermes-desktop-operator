from __future__ import annotations

import asyncio
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Protocol

from desktop_operator.actions.models import (
    ClickAction,
    DoubleClickAction,
    HotkeyAction,
    MoveMouseAction,
    PressKeyAction,
    TypeTextAction,
)


class DesktopController(Protocol):
    async def launch_program(self, program: str, args: list[str]) -> dict[str, Any]: ...
    async def focus_window(self, title_contains: str, timeout: float) -> dict[str, Any]: ...
    async def wait(self, seconds: float) -> dict[str, Any]: ...
    async def move_mouse(self, action: MoveMouseAction) -> dict[str, Any]: ...
    async def click(self, action: ClickAction | DoubleClickAction) -> dict[str, Any]: ...
    async def type_text(self, action: TypeTextAction) -> dict[str, Any]: ...
    async def press_key(self, action: PressKeyAction) -> dict[str, Any]: ...
    async def hotkey(self, action: HotkeyAction) -> dict[str, Any]: ...
    async def screenshot(self, path: Path | None) -> dict[str, Any]: ...
    async def read_active_window(self) -> dict[str, Any]: ...
    async def inspect_ui(self, title_contains: str | None) -> dict[str, Any]: ...


class DryRunController:
    async def launch_program(self, program: str, args: list[str]) -> dict[str, Any]:
        return {"dry_run": True, "program": program, "args": args}

    async def focus_window(self, title_contains: str, timeout: float) -> dict[str, Any]:
        return {"dry_run": True, "title_contains": title_contains, "timeout": timeout}

    async def wait(self, seconds: float) -> dict[str, Any]:
        await asyncio.sleep(min(seconds, 0.01))
        return {"dry_run": True, "seconds": seconds}

    async def move_mouse(self, action: MoveMouseAction) -> dict[str, Any]:
        return {"dry_run": True, "fragile_coordinates": True, "x": action.x, "y": action.y}

    async def click(self, action: ClickAction | DoubleClickAction) -> dict[str, Any]:
        return {"dry_run": True, "target_name": action.target_name, "x": action.x, "y": action.y}

    async def type_text(self, action: TypeTextAction) -> dict[str, Any]:
        return {"dry_run": True, "characters": len(action.text)}

    async def press_key(self, action: PressKeyAction) -> dict[str, Any]:
        return {"dry_run": True, "key": action.key}

    async def hotkey(self, action: HotkeyAction) -> dict[str, Any]:
        return {"dry_run": True, "keys": action.keys}

    async def screenshot(self, path: Path | None) -> dict[str, Any]:
        return {"dry_run": True, "path": str(path) if path else None}

    async def read_active_window(self) -> dict[str, Any]:
        return {"dry_run": True, "title": None}

    async def inspect_ui(self, title_contains: str | None) -> dict[str, Any]:
        return {"dry_run": True, "title_contains": title_contains, "controls": []}


class WindowsController:
    def __init__(self) -> None:
        if platform.system() != "Windows":
            raise RuntimeError("WindowsController is only available on Windows")
        import pyautogui  # type: ignore[import-not-found]
        from pywinauto import Desktop  # type: ignore[import-not-found]

        self.pyautogui = pyautogui
        self.desktop = Desktop(backend="uia")
        self.pyautogui.FAILSAFE = True
        self.last_process_id: int | None = None

    async def launch_program(self, program: str, args: list[str]) -> dict[str, Any]:
        expanded_args = [os.path.expandvars(arg) for arg in args]
        executable = self._resolve_program(program)
        proc = subprocess.Popen([executable, *expanded_args], shell=False)
        self.last_process_id = proc.pid
        return {"pid": proc.pid, "program": program, "executable": executable}

    @staticmethod
    def _resolve_program(program: str) -> str:
        expanded = os.path.expandvars(program)
        if Path(expanded).is_absolute():
            return expanded
        discovered = shutil.which(expanded)
        if discovered:
            return discovered

        try:
            import winreg

            key_path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{expanded}"
            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(root, key_path) as key:
                        registered, _ = winreg.QueryValueEx(key, None)
                        if registered:
                            return str(registered)
                except FileNotFoundError:
                    continue
        except (ImportError, OSError):
            pass
        return expanded

    async def focus_window(self, title_contains: str, timeout: float) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout
        last_error = "window not found"
        while asyncio.get_running_loop().time() < deadline:
            windows = self.desktop.windows(title_re=f".*{title_contains}.*", visible_only=True)
            if windows:
                selected = self._select_window(windows)
                selected.set_focus()
                return {"title": selected.window_text(), "process_id": selected.process_id()}
            await asyncio.sleep(0.25)
        raise TimeoutError(last_error)

    def _select_window(self, windows: list[Any]) -> Any:
        if self.last_process_id:
            for window in windows:
                if window.process_id() == self.last_process_id:
                    return window
        for window in windows:
            if window.window_text().lower().startswith("untitled"):
                return window
        return windows[-1]

    async def wait(self, seconds: float) -> dict[str, Any]:
        await asyncio.sleep(seconds)
        return {"seconds": seconds}

    async def move_mouse(self, action: MoveMouseAction) -> dict[str, Any]:
        self.pyautogui.moveTo(action.x, action.y, duration=action.duration)
        return {"fragile_coordinates": True, "x": action.x, "y": action.y}

    async def click(self, action: ClickAction | DoubleClickAction) -> dict[str, Any]:
        clicks = 2 if action.type == "double_click" else 1
        if action.target_name:
            control = self.desktop.window(active_only=True).child_window(title=action.target_name)
            control.click_input(double=clicks == 2)
            return {"target_name": action.target_name, "clicks": clicks}
        self.pyautogui.click(action.x, action.y, clicks=clicks, button=action.button)
        return {"fragile_coordinates": True, "x": action.x, "y": action.y, "clicks": clicks}

    async def type_text(self, action: TypeTextAction) -> dict[str, Any]:
        try:
            import pyperclip  # type: ignore[import-not-found]

            pyperclip.copy(action.text)
            self.pyautogui.hotkey("ctrl", "v")
            method = "clipboard_paste"
        except Exception:
            self.pyautogui.write(action.text, interval=action.interval)
            method = "keyboard_write"
        return {"characters": len(action.text), "method": method}

    async def press_key(self, action: PressKeyAction) -> dict[str, Any]:
        self.pyautogui.press(action.key)
        return {"key": action.key}

    async def hotkey(self, action: HotkeyAction) -> dict[str, Any]:
        self.pyautogui.hotkey(*action.keys)
        return {"keys": action.keys}

    async def screenshot(self, path: Path | None) -> dict[str, Any]:
        target = path or Path("screenshots") / "latest.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        image = self.pyautogui.screenshot()
        image.save(target)
        return {"path": str(target.resolve(strict=False))}

    async def read_active_window(self) -> dict[str, Any]:
        active = self.desktop.window(active_only=True)
        return {"title": active.window_text(), "process_id": active.process_id()}

    async def inspect_ui(self, title_contains: str | None) -> dict[str, Any]:
        window = (
            self.desktop.window(title_re=f".*{title_contains}.*")
            if title_contains
            else self.desktop.window(active_only=True)
        )
        controls = [
            {"name": child.window_text(), "control_type": child.friendly_class_name()}
            for child in window.descendants()[:100]
        ]
        return {"title": window.window_text(), "controls": controls}


def create_controller(dry_run: bool) -> DesktopController:
    if dry_run or platform.system() != "Windows" or os.environ.get("CI"):
        return DryRunController()
    return WindowsController()
