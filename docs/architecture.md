# Architecture

Hermes Desktop Operator is a localhost-only Windows automation daemon.

## Components

- `api`: FastAPI routes for health, task submission, task inspection, and cancellation.
- `actions`: Pydantic discriminated union schemas. Unknown action types and extra fields fail validation.
- `executor`: Runs one task at a time per submitted background task, applies safety checks, logs each action, and persists snapshots.
- `windows`: Desktop controller abstraction. The real Windows implementation uses UI Automation where possible and software-controlled mouse/keyboard input for execution. A dry-run controller supports tests and non-GUI environments.
- `planner`: Optional Ollama adapter. Natural-language planning is validated against the same action schema before execution.
- `safety`: Program and filesystem allowlists plus approval checks for risky operations.
- `storage`: JSON task snapshots on local disk.
- `logging`: JSON-lines audit log.
- `hermes`: Small client that Hermes can import or invoke.

## Request Flow

1. Hermes or a user calls `POST /tasks` with actions or a natural-language instruction.
2. If an instruction is supplied, Ollama is asked to return JSON actions only.
3. Pydantic validates the strict action schema.
4. The runner stores the task, writes an audit event, and executes actions.
5. Each action is safety-checked before execution.
6. Results and errors are persisted and can be fetched with `GET /tasks/{task_id}`.

## Local-Only Boundary

The daemon defaults to `127.0.0.1` and rejects non-loopback host settings. It is intended for local Hermes-to-desktop communication, not internet exposure.
