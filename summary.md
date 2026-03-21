# AI CLI Relay Orchestrator — 프로젝트 요약

> 작성일: 2026-03-21

---

## 1. 프로젝트 개요

Slack 메시지를 수신해 Windows 11 PC에서 AI CLI(Claude, Gemini, Codex, Cursor)를
서브프로세스로 실행하고, 결과를 실시간으로 Slack 스레드에 스트리밍하는 개인용 원격 제어 서버.

```
스마트폰 Slack
  └─▶ skill[core:claude] 요청
        │  (Socket Mode WebSocket — 포트포워딩 불필요)
  Windows PC
        │  claude --print --dangerously-skip-permissions "..."
        ▼
  Slack 스레드 (실시간 스트리밍)
```

---

## 2. 핵심 설계 결정

### 2-1. Slack Socket Mode (HTTP 웹훅 → WebSocket 전환)
- **문제**: HTTP 웹훅 방식은 공유기 포트포워딩 또는 ngrok 필요
- **결정**: Socket Mode — 서버가 Slack 서버로 아웃바운드 WebSocket 연결
- **효과**: 공유기·방화벽 설정 불필요, NAT 뒤 어디서나 동작
- **필요 토큰**: `SLACK_APP_TOKEN` (`xapp-1-...`) 추가

### 2-2. asyncio.create_task() (Celery + Redis 제거)
- **문제**: Windows는 `os.fork()` 미지원 → Celery `prefork` 풀 동작 불가
- **결정**: `asyncio.create_task()` + `asyncio.wait_for()` 로 대체
- **효과**: Redis 의존성 제거, Windows 네이티브 동작, 코드 단순화

### 2-3. 멀티 CLI 병렬 라우팅
- **문제**: `SELECTED_CLI` 환경변수로 서버 전체 CLI를 고정 → 요청마다 다른 CLI 사용 불가
- **결정**: `skill[name:cli1,cli2]` 문법으로 요청 단위 CLI 지정
- **효과**: 한 요청에서 Claude + Gemini 동시 실행, 결과 비교 가능

### 2-4. WindowsProactorEventLoopPolicy
- Windows에서 `asyncio.create_subprocess_exec()` 동작을 위해 필요
- Python 3.14에서 deprecated → `sys.stdout.reconfigure()` 방식으로 대체

---

## 3. 개발 과정에서 발견·수정한 버그

| # | 버그 | 원인 | 수정 |
|---|------|------|------|
| 1 | `SlackThrottler` 연결 안 됨 | 스트리밍 루프 내 `pass`만 있었음 | `throttler.ingest_log(line)` 연결 |
| 2 | Celery 태스크 큐잉 안 됨 | `.delay()` 호출 주석 처리 상태 | asyncio.create_task()로 전면 교체 |
| 3 | 스킬 경로 하드코딩 | `c:\Users\user\...` 절대경로 | `SKILL_BASE_PATH` 환경변수로 추출 |
| 4 | `.env` 자동 로드 없음 | bat 파일 env 로드 실패 시 토큰 None | `python-dotenv` + `load_dotenv()` 도입 |
| 5 | `UnicodeEncodeError` | Windows cp949 터미널이 em-dash 출력 불가 | `stdout.reconfigure(utf-8)` + `PYTHONUTF8=1` |
| 6 | bat 파일 명령어 오류 | 한국어 주석이 cp949로 깨져 명령어로 실행됨 | bat 파일 영문 전용으로 재작성 |
| 7 | Claude 응답 없음 | `CLAUDECODE` 환경변수가 중첩 세션 차단 | 서브프로세스 env에서 `CLAUDECODE` 키 제거 |
| 8 | 봇 메시지 수신 후 무반응 | Event Subscriptions 미설정 | Slack 앱 대시보드에서 4개 이벤트 등록 |
| 9 | SKILL_PATTERN 매칭 실패 | 봇 멘션 포함 시 텍스트가 `<@ID> skill[...]` 형태 | `(?:<@[A-Z0-9]+>\s*)?` prefix 추가 |
| 10 | `handle_skill_request` 미실행 | `@app.event("message")`가 먼저 이벤트 소비 | 디버그 핸들러 제거, Bolt 리스너 단일화 |

---

## 4. 아키텍처 (현재 상태)

```
main.py
  load_dotenv()
  stdout.reconfigure(utf-8)
  AsyncSocketModeHandler.start_async()
    │
    └─ commands.py: register_listeners()
         @app.message(SKILL_PATTERN)
           ├─ 멘션 포함/미포함 메시지 파싱
           ├─ skill_name, cli_targets 추출
           ├─ ack 메시지 → Slack 스레드 (요청 프롬프트 표시)
           └─ asyncio.create_task(run_langgraph_pipeline × N)
                │
                └─ tasks.py: run_langgraph_pipeline()
                     ├─ SkillLoader: SKILL.md → 시스템 프롬프트 로드
                     ├─ _get_adapter(): ClaudeCLIAdapter 등 선택
                     ├─ adapter.submit(): subprocess 기동
                     │   └─ env에서 CLAUDECODE 제거 (중첩 세션 방지)
                     ├─ adapter.stream(): stdout 라인 스트리밍
                     └─ SlackThrottler: 1초 debounce → chat.update
                          └─ 4000자 초과 시 새 메시지로 페이지네이션
```

---

## 5. 환경변수 전체 목록

| 변수 | 필수 | 기본값 | 설명 |
|------|:----:|--------|------|
| `SLACK_BOT_TOKEN` | ✅ | — | Bot OAuth Token (`xoxb-...`) |
| `SLACK_APP_TOKEN` | ✅ | — | Socket Mode App Token (`xapp-1-...`) |
| `DEFAULT_CLI` | | `claude` | CLI 미지정 시 기본값 |
| `SELECTED_CLI` | | — | `DEFAULT_CLI` 구버전 별칭 (하위 호환) |
| `SKILL_BASE_PATH` | | `~/.gemini/antigravity/skills` | 스킬 파일 루트 경로 |
| `WORKSPACE_PATH` | | `~/workspace` | CLI 서브프로세스 작업 디렉토리 |
| `JOB_TIMEOUT` | | `300` | 작업 타임아웃 (초) |
| `GEMINI_API_KEY` | | — | Gemini CLI API Key |
| `OPENAI_API_KEY` | | — | Codex CLI API Key (필수) |
| `CURSOR_AGENT_BIN` | | `cursor` | Cursor 바이너리 경로 |

---

## 6. 명령어 형식

| 입력 | 동작 |
|------|------|
| `skill[core] 작업` | DEFAULT_CLI 단일 실행 |
| `skill[core:claude] 작업` | Claude 단일 실행 |
| `skill[core:claude,gemini] 작업` | Claude + Gemini 병렬 실행 |
| `skill[core:all] 작업` | 4개 CLI 전체 병렬 실행 |
| `@봇이름 skill[core:claude] 작업` | 멘션 포함도 동일하게 처리 |

---

## 7. 스킬 파일 구조

```
$SKILL_BASE_PATH/
  core/
    SKILL.md       ← YAML frontmatter + 시스템 프롬프트 본문
  review/
    SKILL.md
  ...
```

`SKILL.md` 형식:
```markdown
---
name: core
description: 범용 개발 작업
---

당신은 시니어 소프트웨어 엔지니어입니다.
사용자의 요청을 분석하고 코드를 작성하거나 개선합니다.
```

서버 재시작 없이 파일 수정만으로 즉시 반영됩니다.

---

## 8. CLI별 서버 모드 플래그

| CLI | 설치 | 서버 모드 플래그 | 인증 |
|-----|------|----------------|------|
| Claude | `npm i -g @anthropic-ai/claude-code` | `--print --dangerously-skip-permissions` | 브라우저 1회 로그인 |
| Gemini | `npm i -g @google/gemini-cli` | `--yolo` | 브라우저 or `GEMINI_API_KEY` |
| Codex | `npm i -g @openai/codex` | `--approval-mode full-auto` | `OPENAI_API_KEY` 필수 |
| Cursor | Cursor IDE 설치 | `agent --no-confirm` | Cursor IDE 로그인 |

---

## 9. 알려진 한계 및 향후 개선 포인트

| 항목 | 현황 | 개선 방향 |
|------|------|-----------|
| 로깅 | `print()` 사용 | `logging` 모듈 또는 `structlog` 전환 |
| 동시 작업 제한 없음 | 요청 몰리면 프로세스 폭증 | `asyncio.Semaphore`로 병렬 수 제한 |
| 작업 취소 불가 | 시작한 job을 중간에 멈출 수 없음 | `/cancel {job_id}` 슬래시 커맨드 추가 |
| LangGraph Supervisor 미구현 | `orchestrator_node`가 빈 반환 | 멀티 에이전트 라우팅 로직 구현 |
| 단일 서버 전제 | asyncio.create_task 기반 | 분산 필요 시 Celery + Redis 재도입 |
| Slack API 재시도 없음 | 일시적 실패 시 메시지 유실 | tenacity 기반 exponential backoff |

---

## 10. 주요 파일

| 파일 | 역할 |
|------|------|
| `ai_cli_relay/app/main.py` | 서버 진입점, Socket Mode 핸들러 |
| `ai_cli_relay/app/bot/commands.py` | Slack 메시지 리스너, 파싱, 태스크 디스패치 |
| `ai_cli_relay/app/worker/tasks.py` | 파이프라인 코어 (스킬 로드 → CLI 실행 → 스트리밍) |
| `ai_cli_relay/app/bot/slack_throttler.py` | debounce + 페이지네이션 Slack 업데이터 |
| `ai_cli_relay/app/adapters/base.py` | `BaseCLIAdapter` + `JobSpec` 인터페이스 |
| `ai_cli_relay/app/adapters/claude.py` | Claude CLI 서브프로세스 래퍼 |
| `ai_cli_relay/app/worker/skill_loader.py` | SKILL.md 파일 로더 |
| `start_server.bat` | Windows 서버 시작 스크립트 |
| `.env` | 환경변수 설정 (토큰, 경로) |
| `SETUP_MANUAL.md` | 초보자용 전체 셋업 가이드 |
| `SERVER_MANUAL.md` | 서버 운영 가이드 |
| `CLAUDE.md` | AI 에이전트용 프로젝트 규칙 |
