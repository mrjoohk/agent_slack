# AI CLI Orchestration via Slack (Relay-Based Architecture)

## Date
2026-03-19

---

## 1. Conclusion

There is currently **no complete open-source solution** that provides:

- Slack-based command interface  
- Multi-AI CLI orchestration (Claude, Cursor, Gemini, Codex)  
- Relay-based execution (no direct SSH)  
- Real-time monitoring & logging  

However, **70% of required components exist**, and the remaining 30% (CLI orchestration layer) must be implemented.

---

## 2. Requirements

This system must support:

1. Mixed orchestration across multiple AI CLIs  
2. Single-CLI orchestration mode  
3. CLI-based execution (not API-only)  
4. Relay-based execution (no direct SSH from user)  

---

## 3. High-Level Architecture

```
Slack
  ↓
Relay Bot (Socket Mode)
  ↓
Orchestrator API
  ↓
Job Queue (Redis)
  ↓
Worker (Docker / Local Sandbox)
  ↓
CLI Adapter Layer
  ↓
Claude / Cursor / Gemini / Codex CLI
```

---

## 4. Modes of Operation

### 4.1 Mixed CLI Orchestration

Multiple CLIs collaborate on a single task.

#### Example Flow:
1. Claude → Task planning
2. Cursor → Codebase navigation
3. Codex → Code modification & testing
4. Gemini → Tool-based validation
5. Aggregator → Final result synthesis

#### Components:
- Planner
- Router
- Executor
- Aggregator
- Monitor

#### Pros:
- Best quality
- Leverages strengths of each CLI

#### Cons:
- Complex
- Harder to debug
- Higher cost

---

### 4.2 Single CLI Orchestration (Recommended MVP)

Only one CLI is used per job.

#### Example:
```
/ai run mode=claude ...
/ai run mode=codex ...
```

#### Common Interface:
- submit(job_spec)
- stream(job_id)
- status(job_id)
- cancel(job_id)
- collect_artifacts(job_id)

#### Pros:
- Simple
- Stable
- Fast to implement

#### Cons:
- Less flexibility

---

## 5. Relay-Based Execution (No SSH)

### Why Not SSH?
- Poor traceability
- Hard to manage sessions
- Security risks
- No structured logging

### Recommended Execution Models

#### Option A: Docker Worker (Recommended)
- Isolated environment per job
- Clean reproducibility
- Safe execution

#### Option B: Local Sandbox
- Faster setup
- Less isolation
- Suitable for MVP

---

## 6. Open Source Coverage

### Available Components

- Slack SDK (Bolt + Socket Mode)
- Gemini CLI (open-source)
- Codex CLI (open-source)
- ChatOps frameworks (StackStorm, Hubot)

### Missing Components

- Multi-CLI orchestration layer
- Unified CLI adapter interface
- Streaming normalization
- Slack thread-based monitoring
- Result aggregation logic

---

## 7. Implementation Strategy

### Phase 1: MVP (Single CLI)
- Slack Bot (Bolt)
- FastAPI Orchestrator
- Redis Queue
- Docker Worker
- One CLI Adapter
- Basic logging + status

### Phase 2: Multi-CLI Expansion
- Planner module
- Routing logic
- Aggregator
- Parallel execution support
- Conflict resolution

---

## 8. Key Design Principles

1. Slack is UI only (never execute directly)
2. All executions go through Orchestrator
3. Each job has a unique Job ID
4. Logs and summaries are separated
5. Must support stop / retry / timeout

---

## 9. Final Summary

- No full open-source system exists
- Core building blocks are available
- Missing layer = orchestration + adapter
- Best approach:
  - Start with single CLI orchestration
  - Expand to multi-CLI orchestration

---

## 10. One-Line Insight

**This system is essentially a "ChatOps-based AI CLI Orchestrator" that combines Slack + Workers + CLI Agents.**
