# AI CLI Relay Orchestrator

스마트폰 Slack에서 메시지를 보내면, Windows PC에서 AI CLI(Claude, Gemini, Codex, Cursor)가 실행되고 결과가 Slack 스레드에 실시간으로 스트리밍되는 개인용 원격 제어 서버.

```
스마트폰 Slack
  └─▶ agent[claude] skill[core] 피보나치 수열 구현해줘
        │  (Socket Mode WebSocket — 포트포워딩 불필요)
  Windows PC
        │  claude --print --dangerously-skip-permissions "..."
        ▼
  Slack 스레드 (실시간 스트리밍)
```

---

## 특징

- **포트포워딩 불필요** — Slack Socket Mode(아웃바운드 WebSocket) 사용
- **멀티 CLI 병렬 실행** — 한 요청으로 Claude + Gemini 동시 실행, 결과 비교
- **스킬 시스템** — `SKILL.md` 파일로 시스템 프롬프트 관리 (서버 재시작 불필요)
- **실시간 스트리밍** — CLI 출력이 Slack 메시지로 1초 단위 debounce 업데이트
- **Windows 네이티브** — Celery/Redis 없이 `asyncio.create_task()` 사용

---

## 명령어 형식

| 입력 | 동작 |
|------|------|
| `agent[claude] skill[core] 작업` | Claude 단일 실행 + core 스킬 |
| `agent[gemini] skill[core] 작업` | Gemini 단일 실행 + core 스킬 |
| `agent[claude,gemini] skill[core] 작업` | Claude + Gemini 병렬 실행 |
| `agent[all] skill[core] 작업` | 4개 CLI 전체 병렬 실행 |
| `agent[claude] 작업` | 스킬 없이 Claude 직접 실행 |

지원 CLI: `claude`, `gemini`, `codex`, `cursor`

---

## 빠른 시작

1. **저장소 클론**
   ```bash
   git clone https://github.com/mrjoohk/agent_slack.git
   cd agent_slack
   ```

2. **가상환경 및 의존성 설치**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **환경변수 설정** — `.env` 파일 생성:
   ```env
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-1-...
   SKILL_BASE_PATH=C:\Users\yourname\skills
   WORKSPACE_PATH=C:\Users\yourname\workspace
   ```

4. **서버 실행**
   ```bash
   start_server.bat
   # 또는
   python -m ai_cli_relay.app.main
   ```

전체 셋업 가이드: [SETUP_MANUAL.md](SETUP_MANUAL.md)
서버 운영 가이드: [SERVER_MANUAL.md](SERVER_MANUAL.md)

---

## 스킬 파일 구조

```
$SKILL_BASE_PATH/
  core/
    SKILL.md
  review/
    SKILL.md
```

`SKILL.md` 예시:
```markdown
---
name: core
description: 범용 개발 작업
---

당신은 시니어 소프트웨어 엔지니어입니다.
사용자의 요청을 분석하고 코드를 작성하거나 개선합니다.
```

---

## 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|:----:|--------|------|
| `SLACK_BOT_TOKEN` | ✅ | — | Bot OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | ✅ | — | Socket Mode App Token (`xapp-1-...`) |
| `DEFAULT_CLI` | | `claude` | CLI 미지정 시 기본값 |
| `SKILL_BASE_PATH` | | `~/.gemini/antigravity/skills` | 스킬 파일 루트 경로 |
| `WORKSPACE_PATH` | | `~/workspace` | CLI 서브프로세스 작업 디렉토리 |
| `JOB_TIMEOUT` | | `300` | 작업 타임아웃 (초) |

---

## 아키텍처

```
main.py  (AsyncSocketModeHandler)
  └─ commands.py  (Slack 메시지 파싱 → asyncio.create_task × N)
       └─ tasks.py  (SkillLoader → CLI Adapter → SlackThrottler)
            └─ subprocess  (claude / gemini / codex / cursor)
                 └─ SlackThrottler → Slack chat.update (1s debounce)
```

---

## CLI별 서버 모드 플래그

| CLI | 설치 | 서버 모드 플래그 |
|-----|------|----------------|
| Claude | `npm i -g @anthropic-ai/claude-code` | `--print --dangerously-skip-permissions` |
| Gemini | `npm i -g @google/gemini-cli` | `--yolo` |
| Codex | `npm i -g @openai/codex` | `--approval-mode full-auto` |
| Cursor | Cursor IDE 설치 | `agent --no-confirm` |

---

## 주요 파일

| 파일 | 역할 |
|------|------|
| `ai_cli_relay/app/main.py` | 서버 진입점, Socket Mode 핸들러 |
| `ai_cli_relay/app/bot/commands.py` | Slack 메시지 리스너, 파싱, 태스크 디스패치 |
| `ai_cli_relay/app/worker/tasks.py` | 파이프라인 코어 (스킬 로드 → CLI 실행 → 스트리밍) |
| `ai_cli_relay/app/bot/slack_throttler.py` | debounce + 페이지네이션 Slack 업데이터 |
| `ai_cli_relay/app/adapters/claude.py` | Claude CLI 서브프로세스 래퍼 |
| `ai_cli_relay/app/worker/skill_loader.py` | SKILL.md 파일 로더 |
| `start_server.bat` | Windows 서버 시작 스크립트 |
| `SETUP_MANUAL.md` | 초보자용 전체 셋업 가이드 |
| `summary.md` | 프로젝트 설계 결정 및 버그 수정 기록 |
