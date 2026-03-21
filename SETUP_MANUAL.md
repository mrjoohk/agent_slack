# AI CLI Relay Orchestrator — 설치 및 사용 매뉴얼

> **목표**: Windows 11 PC에서 서버를 실행하고, 스마트폰 Slack 앱에서
> `skill[스킬명] 프롬프트` 를 입력하면 서버 PC의 AI CLI(Claude 등)가 작업을 수행하고
> 결과를 Slack 스레드로 돌려받는 환경을 구성합니다.

---

## 왜 포트포워딩이 필요 없는가

이 서버는 **Slack Socket Mode** 를 사용합니다.

| 방식 | 연결 방향 | 포트포워딩 |
|------|----------|-----------|
| HTTP 웹훅 (기존) | Slack → 내 서버 (인바운드) | **필요** |
| **Socket Mode (현재)** | **내 서버 → Slack (아웃바운드 WebSocket)** | **불필요** |

서버가 Slack의 WebSocket 서버에 먼저 연결을 맺고, Slack이 그 소켓으로 이벤트를 밀어 넣습니다.
공유기 방화벽을 전혀 건드리지 않아도 되고, ngrok 같은 터널링 도구도 필요 없습니다.

```
[스마트폰 Slack]
  → skill[core] 리팩토링해줘
    → Slack 서버 (클라우드)
      → WebSocket (아웃바운드, 서버가 먼저 연결)
        → Windows 11 PC (FastAPI 없음, 포트 불필요)
          → asyncio.create_task()
            → claude --print "..."
              → 결과 스트리밍
                → [스마트폰 Slack 스레드]
```

---

## 1단계 — PC 사전 준비

### 1-1. Python 3.10 이상 확인

```powershell
python --version
# Python 3.10.x 이상이어야 함
```

없으면 https://www.python.org/downloads/ 에서 설치.
설치 시 **"Add Python to PATH"** 체크 필수.

### 1-2. Node.js 확인 (Claude CLI 전용)

```powershell
node --version   # v18 이상 권장
npm --version
```

없으면 https://nodejs.org/ 에서 LTS 버전 설치.

### 1-3. Claude CLI 설치

```powershell
npm install -g @anthropic-ai/claude-code
claude --version   # 설치 확인
```

> 다른 CLI(Gemini, Codex 등)를 쓸 경우 해당 CLI를 대신 설치하고
> 환경변수 `SELECTED_CLI`를 변경합니다 (3단계 참고).

---

## 2단계 — 프로젝트 설치

### 2-1. 저장소 클론

```powershell
git clone https://github.com/mrjoohk/agent_slack.git
cd agent_slack
```

### 2-2. 가상환경 생성 및 활성화

```powershell
python -m venv .venv
.venv\Scripts\activate
# 프롬프트 앞에 (.venv) 가 붙으면 성공
```

### 2-3. 패키지 설치

```powershell
pip install slack_bolt websockets pydantic openpyxl
```

---

## 3단계 — 환경변수 파일(.env) 작성

프로젝트 루트(`agent_slack/`)에 `.env` 파일을 새로 만듭니다.

```env
# Slack Bot Token (4단계에서 발급)
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx

# Slack App-Level Token — Socket Mode 전용 (4단계에서 발급)
# xapp- 로 시작, xoxb- 와 다른 별도 토큰임
SLACK_APP_TOKEN=xapp-1-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx

# 사용할 AI CLI 종류: claude | cursor | gemini | codex
SELECTED_CLI=claude

# 스킬 파일 디렉토리
SKILL_BASE_PATH=C:\Users\user\.gemini\antigravity\skills

# CLI가 작업을 수행할 워크스페이스 디렉토리
WORKSPACE_PATH=C:\Users\user\workspace

# 작업 타임아웃 (초)
JOB_TIMEOUT=300
```

> **주의**: HTTP 웹훅 방식에서 사용하던 `SLACK_SIGNING_SECRET`은
> Socket Mode에서는 불필요합니다. 설정해도 무방하지만 없어도 됩니다.

---

## 4단계 — Slack 앱 생성 및 토큰 발급

### 4-1. 앱 생성

1. https://api.slack.com/apps 접속 → **Create New App** 클릭
2. **From scratch** 선택
3. App Name: `AI-CLI-Bot` (원하는 이름), Workspace 선택 → **Create App**

### 4-2. Socket Mode 활성화 ★ 핵심

1. 좌측 메뉴 **Settings → Socket Mode** 클릭
2. **Enable Socket Mode** 토글 → **ON**
3. Token Name: `socket-token` 입력 → **Generate** 클릭
4. `xapp-1-...` 형식의 **App-Level Token** 복사 → `.env`의 `SLACK_APP_TOKEN`에 붙여넣기

> 이 토큰이 포트포워딩 없이 Slack에 연결되는 핵심입니다.

### 4-3. Bot Token Scopes 설정

좌측 메뉴 **OAuth & Permissions → Scopes → Bot Token Scopes** 에서 아래 추가:

| Scope | 용도 |
|-------|------|
| `chat:write` | 메시지 전송 |
| `chat:write.public` | 멤버가 아닌 채널에도 전송 |
| `channels:history` | 공개 채널 메시지 읽기 |
| `groups:history` | 비공개 채널 메시지 읽기 |
| `im:history` | 다이렉트 메시지 읽기 |
| `mpim:history` | 그룹 DM 메시지 읽기 |

### 4-4. 앱 설치 및 Bot Token 복사

1. **OAuth & Permissions** 상단 → **Install to Workspace** → 허용
2. **Bot User OAuth Token** (`xoxb-...`) 복사 → `.env`의 `SLACK_BOT_TOKEN`에 붙여넣기

### 4-5. Event Subscriptions 활성화

1. 좌측 메뉴 **Event Subscriptions** → **Enable Events** 토글 → **ON**
2. **Subscribe to bot events → Add Bot User Event** 에서 아래 4개 추가:

| Event |
|-------|
| `message.channels` |
| `message.groups` |
| `message.im` |
| `message.mpim` |

3. **Save Changes**

> ⚠️ Socket Mode에서는 **Request URL 입력이 필요 없습니다.** URL 필드가 있어도 비워두면 됩니다.

---

## 5단계 — 스킬 파일 작성

봇이 `skill[스킬명]` 을 받으면 해당 SKILL.md를 AI에게 시스템 프롬프트로 전달합니다.

### 5-1. 디렉토리 생성

```powershell
mkdir "C:\Users\user\.gemini\antigravity\skills\core"
```

### 5-2. SKILL.md 작성

`C:\Users\user\.gemini\antigravity\skills\core\SKILL.md`

```markdown
---
name: core
description: 범용 개발 작업 스킬
---

당신은 시니어 소프트웨어 엔지니어입니다.
사용자의 요청을 분석하고 코드를 작성하거나 개선합니다.
간결하고 명확한 결과물을 제공하세요.
```

---

## 6단계 — 서버 실행

PowerShell을 열고 가상환경을 활성화한 뒤:

```powershell
cd C:\Users\user\AI_TOOLS\agent_orchestration

# 가상환경 활성화
.venv\Scripts\activate

# .env 환경변수 로드
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# 서버 실행 (uvicorn 불필요 — 직접 실행)
python -m ai_cli_relay.app.main
```

정상 기동 시 출력:

```
[AI CLI Bot] Socket Mode 시작 — 포트포워딩 불필요, Slack 서버로 아웃바운드 연결
⚡️ Bolt app is running! (Socket Mode)
```

> HTTP 웹훅 방식과 달리 uvicorn, ngrok 없이 이 한 줄로 모든 것이 동작합니다.

---

## 7단계 — Slack에 봇 초대

메시지를 보낼 채널에 봇을 초대합니다.

```
/invite @AI-CLI-Bot
```

> DM으로 바로 사용하려면 Slack 앱에서 봇을 직접 찾아 DM을 시작합니다.

---

## 8단계 — 스마트폰 Slack에서 사용

### 메시지 형식

```
skill[스킬명] 요청 내용
```

### 예시

```
skill[core] 피보나치 수열을 Python으로 구현해줘
```

```
skill[core] 이 함수의 버그를 찾아줘:
def divide(a, b):
    return a / b
```

### 예상 응답 흐름

1. 봇이 즉시 스레드에 응답:
   ```
   ⏳ [core] 작업을 시작합니다... (Job: a1b2c3d4)
   > 피보나치 수열을 Python으로 구현해줘
   ```

2. CLI 실행 결과가 실시간으로 업데이트:
   ```
   def fibonacci(n):
       if n <= 1:
           return n
       return fibonacci(n-1) + fibonacci(n-2)
   ```

3. 결과가 3,900자 초과 시 자동으로 다음 스레드 메시지로 이어짐.

---

## 자주 발생하는 문제

### ❌ `xapp-` 토큰을 찾을 수 없음

Socket Mode가 활성화되지 않은 상태입니다.
**Settings → Socket Mode → Enable Socket Mode** 를 먼저 켜고 토큰을 생성하세요.

### ❌ 서버 시작 시 `SLACK_APP_TOKEN is not set` 또는 연결 오류

`.env` 파일의 `SLACK_APP_TOKEN`이 비어있거나 환경변수 로드가 안 된 상태입니다.
환경변수 로드 명령어를 다시 실행하세요.

### ❌ 봇이 메시지에 응답하지 않음

- 채널에 봇이 초대되어 있는지 확인 (`/invite @봇이름`)
- 메시지 형식 확인: `skill[스킬명] 프롬프트`
- 서버 콘솔에 이벤트 수신 로그가 찍히는지 확인

### ❌ `ModuleNotFoundError: No module named 'slack_bolt'`

```powershell
pip install slack_bolt websockets
```

### ❌ `FileNotFoundError: Skill 'xxx' not found`

`SKILL_BASE_PATH` 아래 `<스킬명>/SKILL.md` 파일이 있는지 확인.
5단계 스킬 파일 생성 절차를 재확인하세요.

### ❌ Socket Mode 연결 후 바로 끊김

App-Level Token(`xapp-...`)에 `connections:write` 스코프가 있는지 확인:
**Slack API Dashboard → Your App → Basic Information → App-Level Tokens**
토큰 클릭 → Scopes에 `connections:write` 있어야 함.

---

## 환경변수 빠른 참조

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `SLACK_BOT_TOKEN` | ✅ | — | `xoxb-...` Slack Bot Token |
| `SLACK_APP_TOKEN` | ✅ | — | `xapp-...` App-Level Token (Socket Mode 전용) |
| `SELECTED_CLI` | | `claude` | `claude`, `cursor`, `gemini`, `codex` |
| `SKILL_BASE_PATH` | | `~/.gemini/antigravity/skills` | 스킬 디렉토리 루트 |
| `WORKSPACE_PATH` | | `~/workspace` | CLI 작업 디렉토리 |
| `JOB_TIMEOUT` | | `300` | 작업 타임아웃 (초) |

---

## HTTP 웹훅 방식과 비교

| 항목 | HTTP 웹훅 (구버전) | Socket Mode (현재) |
|------|------------------|------------------|
| 연결 방향 | Slack → 서버 (인바운드) | 서버 → Slack (아웃바운드) |
| 포트포워딩 | 필요 | **불필요** |
| ngrok | 필요 | **불필요** |
| 공인 IP | 필요 | **불필요** |
| 실행 명령어 | `uvicorn ... + ngrok http 8000` | `python -m ai_cli_relay.app.main` |
| 필요 토큰 | BOT_TOKEN + SIGNING_SECRET | BOT_TOKEN + APP_TOKEN |
