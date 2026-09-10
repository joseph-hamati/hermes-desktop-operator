from __future__ import annotations

import platform
from collections.abc import Callable


class EmergencyStopHotkey:
    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self.hotkey = hotkey
        self.callback = callback
        self.available = False
        self.error: str | None = None

    def start(self) -> None:
        if platform.system() != "Windows":
            self.error = "global hotkey is only enabled on Windows"
            return
        try:
            import keyboard  # type: ignore[import-not-found]

            keyboard.add_hotkey(self.hotkey, self.callback, suppress=False)
            self.available = True
        except Exception as exc:
            self.error = str(exc)
