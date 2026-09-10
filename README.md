# Hermes Desktop Operator

Hermes Desktop Operator is a local Windows automation daemon. It receives structured desktop actions from Hermes, optionally asks a local Ollama model to turn natural language into those actions, executes them with software-controlled Windows input, observes results, and writes an audit trail.

This MVP is deliberately narrow: no arbitrary code execution, no shell commands from model output, no cloud dependency, and localhost-only by default.

## Requirements

- Windows 11
- Python 3.12+
- Ollama running locally for natural-language planning
- Interactive desktop session for real UI automation

## Install

```powershell
git clone https://github.com/<your-account>/hermes-desktop-operator.git
cd hermes-desktop-operator
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install_windows.ps1
notepad .env
```

Set a local token in `.env`:

```text
HERMES_OPERATOR_API_TOKEN=use-a-long-random-local-token
```

## Ollama Setup

```powershell
ollama pull llama3.1:8b
ollama serve
```

Configure another local model in `.env`:

```text
HERMES_OPERATOR_OLLAMA_URL=http://127.0.0.1:11434
HERMES_OPERATOR_OLLAMA_MODEL=llama3.1:8b
HERMES_OPERATOR_OLLAMA_TEMPERATURE=0.1
```

If Ollama is unavailable, manually supplied JSON actions still work.

## Start the Daemon

```powershell
.\scripts\run_daemon.ps1
```

Health check:

```powershell
curl.exe http://127.0.0.1:8765/health
```

## Run the Notepad Demo

With the daemon running:

```powershell
.\scripts\run_demo.ps1
```

The demo opens Notepad, types `My first desktop-agent test.`, saves it to a unique Desktop file such as:

```text
%USERPROFILE%\Desktop\hermes-desktop-operator-demo-1789040000.txt
```

Then it verifies the file exists and prints the structured task result. It also writes an audit log to `audit/audit.jsonl`.

## Manual Task Submission

```powershell
$token = "use-a-long-random-local-token"
$body = Get-Content .\examples\example_task.json -Raw
curl.exe -X POST http://127.0.0.1:8765/tasks `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  --data $body
```

Poll a task:

```powershell
curl.exe http://127.0.0.1:8765/tasks/<task_id> -H "Authorization: Bearer $token"
```

Cancel a task:

```powershell
curl.exe -X POST http://127.0.0.1:8765/tasks/<task_id>/cancel -H "Authorization: Bearer $token"
```

## Action Schema

Supported actions:

- `launch_program`
- `focus_window`
- `wait`
- `move_mouse`
- `click`
- `double_click`
- `type_text`
- `press_key`
- `hotkey`
- `screenshot`
- `read_active_window`
- `inspect_ui`
- `verify_file_exists`
- `create_directory`
- `save_text_file`

Unknown actions and extra parameters are rejected.

## Safety Model

- API token required for task operations.
- Daemon binds to `127.0.0.1` by default.
- Program allowlist defaults to `notepad.exe,calc.exe`.
- Filesystem allowlist defaults to `%USERPROFILE%\Desktop`.
- `save_text_file` and `create_directory` only work inside allowed directories.
- Existing files are not overwritten unless the task includes `overwrite_files` approval.
- Every action and result is written to the audit log.
- Dry-run mode can be enabled with `HERMES_OPERATOR_DRY_RUN=true`.
- Global and per-action timeouts prevent infinite loops.

Configure allowlists in `.env`:

```text
HERMES_OPERATOR_ALLOWED_PROGRAMS=notepad.exe,calc.exe
HERMES_OPERATOR_ALLOWED_DIRECTORIES=%USERPROFILE%\Desktop,C:\Users\Joseph\Documents\Hermes
```

## Emergency Stop

The daemon attempts to register the global hotkey configured by `HERMES_OPERATOR_EMERGENCY_STOP_HOTKEY`, which defaults to:

```text
ctrl+alt+shift+q
```

When available, pressing it cancels running tasks and writes an `emergency_stop` audit event. Windows permissions and foreground/security context can prevent global hotkey registration, so the cancellation endpoint is also supported:

```powershell
curl.exe -X POST http://127.0.0.1:8765/tasks/<task_id>/cancel -H "Authorization: Bearer $token"
```

Check `/health` for the hotkey registration status.

## Hermes Integration

Install the included Hermes Agent plugin:

```powershell
.\scripts\install_hermes_plugin.ps1 -ConfigureToken
```

The installer detects Hermes's active Windows profile and copies the same
`HERMES_OPERATOR_API_TOKEN` used by the daemon into Hermes's local environment
without printing it. Enable `hermes-desktop-operator` with
`hermes plugins enable hermes-desktop-operator`, then restart Hermes. Keep the
daemon running while Hermes uses the tool.

Hermes can also call the service directly over localhost HTTP:

```python
from desktop_operator.hermes.client import HermesDesktopClient

client = HermesDesktopClient("http://127.0.0.1:8765", "use-a-long-random-local-token")
```

See [docs/hermes-integration.md](docs/hermes-integration.md).

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Windows integration tests are marked `windows_integration` and skipped outside Windows.

## Troubleshooting

- `401 invalid API token`: check `HERMES_OPERATOR_API_TOKEN` and the bearer header.
- Ollama unavailable in `/health`: run `ollama serve` and verify the configured URL.
- Notepad did not focus: make sure the Windows desktop is unlocked and no UAC prompt is active.
- Path rejected: add the parent directory to `HERMES_OPERATOR_ALLOWED_DIRECTORIES`.
- Program rejected: add the executable name to `HERMES_OPERATOR_ALLOWED_PROGRAMS`.

## Clone and Update

```powershell
git clone https://github.com/<your-account>/hermes-desktop-operator.git
cd hermes-desktop-operator
git pull
.\scripts\install_windows.ps1
```
