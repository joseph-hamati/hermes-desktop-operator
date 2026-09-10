# Security Model

Hermes Desktop Operator is intentionally not a general-purpose autonomous agent.

## Defaults

- Binds only to localhost.
- Requires bearer-token authentication.
- Rejects unknown actions, extra fields, and malformed parameters.
- Does not execute model-generated code, shell commands, PowerShell, or Python.
- Uses program and filesystem allowlists.
- Writes a visible audit log for every task and action.
- Supports dry-run execution.
- Uses global and per-action timeouts.
- Supports task cancellation and a best-effort Windows global emergency stop hotkey.

## Approval-Gated Areas

The MVP has no action for deleting files, sending messages, purchasing, changing passwords, changing firewall/security settings, installing software, or interacting with financial/authentication systems. If those are added later, they must require explicit approval and dedicated typed schemas.

Overwriting an existing file is blocked unless:

- the action sets `overwrite: true`
- the task includes the approval token `overwrite_files`
- the target path is inside an allowed directory

## Known Limits

The Windows controller relies on the current interactive user session. UAC prompts, secure desktops, lock screens, elevated applications, remote desktop focus issues, and applications with unusual UI frameworks can block automation. Absolute coordinates are marked as fragile and should be used only as fallback.

The emergency stop hotkey uses Windows keyboard hooks. It can be blocked by permissions, secure desktops, or endpoint protection. Use `POST /tasks/{task_id}/cancel` when a programmatic stop path is required.
