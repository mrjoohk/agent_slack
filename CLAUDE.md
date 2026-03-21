# CLAUDE.md — AI CLI Relay Orchestrator

This workspace is the `agent_orchestration` project: a relay server that receives
user prompts from Slack, executes an AI CLI tool (Claude, Cursor, Gemini, Codex)
as a subprocess on the host machine, and streams results back to Slack in real time.

All agents working in this repo must follow the rules below.

---

## 1. Role

- Act as a senior Python async/API developer.
- Prioritize correctness of the async pipeline, Slack API contract compliance,
  and Windows runtime stability.
- Never break the Slack Bolt ↔ FastAPI integration contract or the
  `BaseCLIAdapter` interface without explicit user approval.

---

## 2. Architecture Overview

```
Slack message
  → POST /slack/events  (FastAPI + Slack Bolt)
    → commands.py       (pattern match, input validation, uuid job_id)
      → asyncio.create_task()
        → tasks.py      (SkillLoader → CLI Adapter → SlackThrottler)
          → subprocess  (claude / cursor / gemini / codex CLI)
            → SlackThrottler → chat.update / chat.postMessage → Slack thread
```

**Key design decisions already made — do not revert without justification:**

- `asyncio.create_task()` is used instead of Celery + Redis.
  Reason: Windows does not support Celery's `prefork` pool (`os.fork`);
  single-server relay use case does not need distributed queues.
- `WindowsProactorEventLoopPolicy` is set at startup in `main.py`.
  Required for `asyncio.create_subprocess_exec()` on Windows.
- All CLI adapters use `shell=False` (array form). Never change to `shell=True`.

---

## 3. Critical Files

| File | Role |
|------|------|
| `ai_cli_relay/app/main.py` | FastAPI + Slack Bolt entry point; Windows asyncio policy |
| `ai_cli_relay/app/bot/commands.py` | Slack message listener; input validation; task dispatch |
| `ai_cli_relay/app/worker/tasks.py` | Core pipeline: skill load → adapter → stream → Slack |
| `ai_cli_relay/app/bot/slack_throttler.py` | Debounced Slack message updater with pagination |
| `ai_cli_relay/app/adapters/base.py` | `BaseCLIAdapter` + `JobSpec` — the adapter contract |
| `ai_cli_relay/app/adapters/claude.py` | Claude CLI subprocess wrapper (primary adapter) |
| `ai_cli_relay/app/worker/skill_loader.py` | Loads SKILL.md from `SKILL_BASE_PATH` |
| `ai_cli_relay/requirements.txt` | Dependencies; Celery/Redis commented out intentionally |

---

## 4. Workflow

1. Understand the request and identify the affected files.
2. Read every file that will be changed before editing it.
3. Share analysis and rationale with the user before making changes.
4. Wait for confirmation on non-trivial or risky changes.
5. Implement; save analysis memos as `YYMMDD_HHMM_<topic>.md` in the repo root.
6. Run a smoke-test or describe a manual verification procedure.
7. Commit with a descriptive message when the user asks.

---

## 5. Codebase Rules

- Target Python is **3.10+**.
- The primary package root is `ai_cli_relay/app/`. Relative imports are used
  throughout — do not restructure the package without explicit approval.
- `BaseCLIAdapter` in `adapters/base.py` defines the interface contract.
  All four adapters (`claude`, `cursor`, `gemini`, `codex`) must implement it.
  Adding a new adapter means subclassing `BaseCLIAdapter`, registering it in
  the `_get_adapter()` factory in `tasks.py`, and nothing else.
- `SlackThrottler` owns the Slack update/post logic. Do not call
  `slack_client.chat_update` or `chat_postMessage` directly from adapters or
  `commands.py`.
- Skill files live at `$SKILL_BASE_PATH/<skill_name>/SKILL.md`.
  Never hardcode a user-specific path (e.g. `c:\Users\user\...`) in source code.
- The `workspace_path` fallback for subprocess `cwd` must be `Path.home()`,
  never a Docker-specific path like `/app/workspace`.

---

## 6. Environment Variables

The server is configured entirely through environment variables. When adding a
new configurable value, always read it with `os.environ.get("KEY", "default")`
and document it here and in `tasks.py`'s docstring.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SLACK_BOT_TOKEN` | *(required)* | Slack bot OAuth token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | *(required)* | Slack webhook signature verification |
| `SELECTED_CLI` | `claude` | CLI adapter to use: `claude\|cursor\|gemini\|codex` |
| `SKILL_BASE_PATH` | `~/.gemini/antigravity/skills` | Root directory for skill YAML/MD files |
| `WORKSPACE_PATH` | `~/workspace` | Working directory passed to the CLI subprocess |
| `JOB_TIMEOUT` | `300` | Seconds before the subprocess is forcibly cancelled |

---

## 7. Coding Style

- Follow PEP 8; keep lines to **88 characters** max.
- Apply type hints to all new or modified functions and methods.
- Write concise docstrings for public functions, classes, and non-obvious logic.
- Use descriptive English names for functions and variables; avoid abbreviations
  and magic numbers.
- Add comments only to explain *why*, not *what*.
- Avoid `print()` for new logging; use `print(f"[{job_id}] ...")` at minimum
  until a proper `logging` module is wired in.

---

## 8. Async Rules

- All Slack Bolt handlers and pipeline functions are `async`. Keep them that way.
- Use `asyncio.create_task()` to fire-and-forget the pipeline from the Bolt
  handler. Do not `await` it inside the handler (Slack's 3-second ack timeout).
- Use `asyncio.wait_for(..., timeout=JOB_TIMEOUT)` around the streaming loop.
  Never let a subprocess stream without a timeout guard.
- The `asyncio.Lock()` inside `SlackThrottler` guards the buffer. Do not
  access `block_buffer` or `current_ts` outside the lock.

---

## 9. Security Rules

- `skill_name` from Slack must be validated against `^[a-zA-Z0-9_-]+$`
  before use in any file path operation. This check already exists in
  `commands.py` — do not remove it.
- CLI commands are always passed as arrays (`shell=False`). Never construct a
  shell string from user-supplied input.
- `workspace_path` should not be taken directly from user input without
  path validation. If adding workspace selection, enforce an allowlist.

---

## 10. Dependencies

- Use existing dependencies first: `fastapi`, `slack_bolt`, `pydantic`, `asyncio`.
- Do not add Celery or Redis unless the user explicitly requests distributed
  multi-server task queuing. The current `asyncio.create_task()` design is
  intentional for single-server Windows deployment.
- Do not add a new library for a task that stdlib or an existing dep can handle.
- When adding a dependency, explain the reason and update `requirements.txt`.

---

## 11. Testing & Verification

- There is no test suite yet. When adding tests, use `pytest` + `pytest-asyncio`.
- Slack API calls and subprocess spawning must be mocked in unit tests.
  Do not make real Slack API calls in tests.
- When automated testing is impractical, provide a **manual smoke-test procedure**
  describing: the Slack message to send, the expected Slack thread output,
  and the expected console log lines.
- Do not claim a test passes if it has not been run.

---

## 12. Output & Documentation Format

| Content type | Format |
|---|---|
| Analysis memos, rationale notes | `.md` (stored in repo root, named `YYMMDD_HHMM_<topic>.md`) |
| Structured data / tracking | `.xlsx` |
| Report with tables/figures | `.docx` |
| Presentation | `.pptx` |

When reporting changes, always include:
- **What** changed and **where** (file + line range).
- **Why** (the problem it solves or the design decision behind it).
- **How to verify** (smoke test steps or expected log output).
