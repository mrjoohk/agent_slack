# AI CLI Relay Orchestrator — 설치 및 사용 매뉴얼

> **목표**: Windows 11 PC에서 서버를 실행하고, 스마트폰 Slack 앱에서
> `skill[스킬명] 프롬프트` 를 입력하면 서버 PC의 AI CLI(Claude 등)가 작업을 수행하고
> 결과를 Slack 스레드로 돌려받는 환경을 구성합니다.

---

## 전체 흐름 요약

```
[스마트폰 Slack]
  → skill[core] 리팩토링해줘
    → (인터넷)
      → ngrok Public URL
        → Windows 11 PC :8000 (FastAPI)
          → asyncio.create_task()
            → claude --print "..."  (서브프로세스)
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
pip install fastapi uvicorn pydantic slack_bolt slack_sdk openpyxl
```

> `requirements.txt`의 `celery`, `redis`, `docker`, `langchain`, `langgraph`는
> 현재 구현에서 사용하지 않으므로 설치하지 않아도 됩니다.

---

## 3단계 — 환경변수 파일(.env) 작성

프로젝트 루트(`agent_slack/`)에 `.env` 파일을 새로 만듭니다.

```env
# Slack Bot 인증 (4단계에서 발급)
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_SIGNING_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 사용할 AI CLI 종류: claude | cursor | gemini | codex
SELECTED_CLI=claude

# 스킬 파일 디렉토리 (아래 경로가 기본값, 변경 가능)
SKILL_BASE_PATH=C:\Users\user\.gemini\antigravity\skills

# CLI가 작업을 수행할 워크스페이스 디렉토리
WORKSPACE_PATH=C:\Users\user\workspace

# 작업 타임아웃 (초). 이 시간 초과 시 프로세스 강제 종료
JOB_TIMEOUT=300
```

> `.env` 파일은 `.gitignore`에 이미 등록되어 있어 Git에 올라가지 않습니다.

---

## 4단계 — Slack 앱 생성 및 토큰 발급

### 4-1. 앱 생성

1. https://api.slack.com/apps 접속 → **Create New App** 클릭
2. **From scratch** 선택
3. App Name: `AI-CLI-Bot` (원하는 이름), Workspace 선택 → **Create App**

### 4-2. Bot Token Scopes 설정

좌측 메뉴 **OAuth & Permissions** → **Scopes** → **Bot Token Scopes** 에서
아래 항목을 모두 추가합니다.

| Scope | 용도 |
|-------|------|
| `chat:write` | 메시지 전송 |
| `chat:write.public` | 멤버가 아닌 채널에도 메시지 전송 |
| `channels:history` | 공개 채널 메시지 읽기 |
| `groups:history` | 비공개 채널 메시지 읽기 |
| `im:history` | 다이렉트 메시지 읽기 |
| `mpim:history` | 그룹 DM 메시지 읽기 |

### 4-3. 앱 워크스페이스 설치 및 토큰 복사

1. 같은 **OAuth & Permissions** 페이지 상단 → **Install to Workspace** 클릭 → 허용
2. **Bot User OAuth Token** (`xoxb-...`) 복사 → `.env`의 `SLACK_BOT_TOKEN`에 붙여넣기

### 4-4. Signing Secret 복사

1. 좌측 메뉴 **Basic Information** → **App Credentials** 섹션
2. **Signing Secret** 옆 **Show** → 복사 → `.env`의 `SLACK_SIGNING_SECRET`에 붙여넣기

### 4-5. Event Subscriptions 활성화 (나중에 URL 입력)

1. 좌측 메뉴 **Event Subscriptions** → **Enable Events** 토글 ON
2. **Subscribe to bot events** → **Add Bot User Event** 에서 아래 4개 추가

| Event | 설명 |
|-------|------|
| `message.channels` | 공개 채널 메시지 |
| `message.groups` | 비공개 채널 메시지 |
| `message.im` | DM 메시지 |
| `message.mpim` | 그룹 DM 메시지 |

> **Request URL은 6단계(ngrok)에서 입력합니다.** 지금은 저장하지 말고 열어두세요.

---

## 5단계 — 스킬 파일 작성

봇이 `skill[스킬명]` 을 받으면 해당 이름의 SKILL.md를 로드해 AI에게 시스템 프롬프트로 전달합니다.

### 5-1. 디렉토리 생성

```powershell
# .env의 SKILL_BASE_PATH 경로에 스킬 폴더 생성
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

> 스킬을 여러 개 만들려면 폴더명만 다르게 해서 반복 생성합니다.
> 예: `skills\refactor\SKILL.md`, `skills\review\SKILL.md`

---

## 6단계 — ngrok 설치 및 외부 URL 생성

핸드폰 Slack → 서버 PC로 연결하려면 PC의 포트를 인터넷에 노출시켜야 합니다.

### 6-1. ngrok 설치

https://ngrok.com/download 에서 Windows용 zip 다운로드 후 압축 해제.
또는 winget으로 설치:

```powershell
winget install ngrok.ngrok
```

### 6-2. ngrok 계정 연결 (무료 플랜)

1. https://ngrok.com 가입 후 로그인
2. Dashboard → **Your Authtoken** 복사
3. 터미널에서 실행:

```powershell
ngrok config add-authtoken <YOUR_AUTHTOKEN>
```

### 6-3. 터널 실행

**서버를 먼저 기동한 후(7단계) 이 명령어를 실행**해도 되고,
URL 확보를 위해 먼저 실행해도 됩니다.

```powershell
ngrok http 8000
```

실행 결과 예시:

```
Forwarding   https://abcd-123-456.ngrok-free.app -> http://localhost:8000
```

`https://abcd-123-456.ngrok-free.app` 부분을 복사합니다.

### 6-4. Slack Event Subscriptions URL 입력

1. 4단계에서 열어둔 Slack API 페이지로 이동
2. **Event Subscriptions** → **Request URL** 에 입력:

```
https://abcd-123-456.ngrok-free.app/slack/events
```

3. **Verified ✓** 체크가 뜨면 성공 → **Save Changes** 클릭

> **주의**: ngrok 무료 플랜은 재시작마다 URL이 바뀝니다.
> URL이 바뀔 때마다 Slack Event Subscriptions의 Request URL을 다시 업데이트해야 합니다.
> 고정 URL이 필요하면 ngrok 유료 플랜 또는 Cloudflare Tunnel을 사용하세요.

---

## 7단계 — 서버 실행

### 7-1. 환경변수 로드 및 서버 기동

PowerShell을 새로 열고 가상환경을 활성화한 뒤:

```powershell
cd C:\Users\user\AI_TOOLS\agent_orchestration

# 가상환경 활성화
.venv\Scripts\activate

# .env 파일 환경변수 로드 (PowerShell)
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# 서버 실행
python -m uvicorn ai_cli_relay.app.main:app --host 0.0.0.0 --port 8000
```

정상 기동 시 출력:

```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 7-2. 헬스체크 확인

브라우저 또는 PowerShell에서:

```powershell
curl http://localhost:8000/health
# 응답: {"status":"ok"}
```

---

## 8단계 — Slack에 봇 초대

### 8-1. 채널에 봇 초대

Slack에서 메시지를 보낼 채널(또는 DM)에 봇을 초대합니다.

```
/invite @AI-CLI-Bot
```

> DM으로 바로 사용하려면 Slack 앱에서 봇을 직접 찾아 DM을 시작합니다.

---

## 9단계 — 스마트폰 Slack에서 사용

### 9-1. 메시지 형식

```
skill[스킬명] 요청 내용
```

예시:

```
skill[core] 피보나치 수열을 Python으로 구현해줘
```

```
skill[core] 이 코드의 버그를 찾아줘:
def add(a, b):
    return a - b
```

### 9-2. 예상 응답 흐름

1. 봇이 즉시 스레드에 답변:
   ```
   ⏳ [core] 작업을 시작합니다... (Job: a1b2c3d4)
   > 피보나치 수열을 Python으로 구현해줘
   ```

2. CLI 실행 결과가 스트리밍으로 업데이트됨:
   ```
   def fibonacci(n):
       if n <= 1:
           return n
       return fibonacci(n-1) + fibonacci(n-2)
   ...
   ```

3. 결과가 3,900자를 초과하면 자동으로 스레드 다음 메시지로 이어짐 (페이지네이션).

---

## 자주 발생하는 문제

### ❌ ngrok URL 입력 후 Slack에서 "Your URL didn't respond with a challenge" 오류

- 서버가 실행 중인지 확인: `curl http://localhost:8000/health`
- ngrok이 실행 중인지 확인: `ngrok http 8000` 터미널 열려 있는지 확인
- URL 끝에 `/slack/events` 가 정확히 붙어 있는지 확인

### ❌ `ModuleNotFoundError: No module named 'slack_bolt'`

```powershell
pip install slack_bolt slack_sdk
```

### ❌ `SLACK_BOT_TOKEN` 또는 `SLACK_SIGNING_SECRET` 관련 오류

- `.env` 파일이 프로젝트 루트에 있는지 확인
- 환경변수 로드 명령어를 다시 실행

### ❌ 봇이 메시지에 응답하지 않음

- 채널에 봇이 초대되어 있는지 확인 (`/invite @봇이름`)
- 메시지 형식이 정확한지 확인: `skill[스킬명] 프롬프트`
- 서버 콘솔에 Slack 이벤트 수신 로그가 찍히는지 확인

### ❌ `FileNotFoundError: Skill 'xxx' not found`

- `SKILL_BASE_PATH` 경로 아래 `<스킬명>/SKILL.md` 파일이 있는지 확인
- 5단계 스킬 파일 생성 절차를 재확인

### ❌ ngrok URL 재시작 후 봇 미응답

- ngrok를 재시작하면 URL이 바뀜
- 새 URL로 Slack **Event Subscriptions → Request URL** 을 업데이트하고 **Save Changes**

### ❌ Windows 방화벽으로 인한 접속 차단

- ngrok은 외부에서 ngrok 서버를 경유해 PC로 들어오므로 일반적으로 방화벽 설정이 불필요
- 만약 로컬 테스트(같은 LAN)에서 문제가 생기면 Windows Defender 방화벽에서 포트 8000 인바운드 허용

---

## 서버 상시 운용 팁

### 터미널 분리 실행 (Windows Terminal 탭 활용)

| 탭 | 역할 | 명령어 |
|----|------|--------|
| Tab 1 | FastAPI 서버 | `python -m uvicorn ai_cli_relay.app.main:app --host 0.0.0.0 --port 8000` |
| Tab 2 | ngrok 터널 | `ngrok http 8000` |

### 고정 URL을 원할 경우

**옵션 A — ngrok 유료 플랜**: 고정 도메인 할당 가능 (월 $10~)

**옵션 B — Cloudflare Tunnel (무료, 고정 URL)**:

```powershell
# Cloudflare Tunnel 설치 후
cloudflared tunnel --url http://localhost:8000
```

**옵션 C — 공유기 포트포워딩 + DDNS**: 공유기 설정에서 8000 포트를 PC IP로 포워딩,
DDNS 서비스(Duck DNS 등)로 고정 도메인 사용.

---

## 환경변수 빠른 참조

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `SLACK_BOT_TOKEN` | ✅ | — | `xoxb-...` 형식의 Slack Bot Token |
| `SLACK_SIGNING_SECRET` | ✅ | — | Slack 앱 Signing Secret |
| `SELECTED_CLI` | | `claude` | `claude`, `cursor`, `gemini`, `codex` |
| `SKILL_BASE_PATH` | | `~/.gemini/antigravity/skills` | 스킬 디렉토리 루트 |
| `WORKSPACE_PATH` | | `~/workspace` | CLI 작업 디렉토리 |
| `JOB_TIMEOUT` | | `300` | 작업 타임아웃 (초) |
