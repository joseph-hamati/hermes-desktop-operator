from __future__ import annotations

import platform

import pytest

pytestmark = pytest.mark.windows_integration


@pytest.mark.skipif(platform.system() != "Windows", reason="requires real Windows desktop")
def test_notepad_demo_documented_for_manual_execution() -> None:
    assert platform.system() == "Windows"
