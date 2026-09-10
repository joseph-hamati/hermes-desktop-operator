# Hermes Integration

Hermes should treat the daemon as a local executor with a narrow contract.

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
