# Hermes Integration

Hermes should treat the daemon as a local executor with a narrow contract.

## Connect Hermes Agent

Install the included user plugin:

```powershell
.\scripts\install_hermes_plugin.ps1 -ConfigureToken
```

This detects Hermes's active Windows profile, then copies the daemon URL and the
existing local token from the project's `.env` into Hermes's `.env` without
printing the token. The resulting settings are:

```text
HERMES_OPERATOR_API_TOKEN=<same local token used by the daemon>
HERMES_OPERATOR_URL=http://127.0.0.1:8765
```

In Hermes Desktop, open **Capabilities > Plugins**, enable
`hermes-desktop-operator`, and restart Hermes. Current Hermes Agent versions keep
third-party plugins disabled until the user explicitly enables them.

Keep `run_daemon.ps1` running. Then ask Hermes:

```text
Use desktop_operator to open Notepad and type Hello from Hermes.
```

Hermes receives `desktop_browser_navigate`, `desktop_operator`,
`desktop_task_status`, and `desktop_task_cancel`. Use `desktop_browser_navigate`
for reliable Chrome address-bar navigation without local model planning. The daemon
still validates every action and enforces its program and filesystem allowlists.

## Configuration

Daemon URL:

```text
http://127.0.0.1:8765
```

Authentication header:

```text
Authorization: Bearer <HERMES_OPERATOR_API_TOKEN>
```

## Submit Structured Actions

```python
import asyncio
from desktop_operator.hermes.client import HermesDesktopClient

async def main():
    client = HermesDesktopClient("http://127.0.0.1:8765", "change-me-local-token")
    created = await client.submit_actions([
        {"type": "launch_program", "program": "notepad.exe"},
        {"type": "focus_window", "title_contains": "Notepad"},
        {"type": "type_text", "text": "Hello from Hermes."}
    ])
    print(created["task_id"])

asyncio.run(main())
```

## Submit Natural Language

Natural-language submission requires Ollama to be running:

```python
created = await client.submit_instruction(
    "Open Notepad and type a short status note."
)
```

The daemon validates the model output before execution.

## Poll Status

```python
task = await client.get_task(task_id)
print(task["status"])
print(task["current_action"])
print(task["actions"])
print(task["errors"])
print(task["summary"])
```

## Cancel

```python
await client.cancel_task(task_id)
```

Hermes should display every action and result to the user. The daemon never hides actions.
