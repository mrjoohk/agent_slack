# 전체 셋업 매뉴얼
## AI CLI Relay Bot — Windows 11 서버 + 스마트폰 Slack 연동

> 이 문서 하나만 따라 하면 Windows 11 PC에서 서버를 실행하고,
> 스마트폰 Slack 앱으로 AI CLI를 원격 제어할 수 있습니다.

---

## 이 시스템이 하는 일

```
스마트폰 Slack
  └─▶ skill[core:claude] 코드 리뷰해줘
        │
        │  (인터넷 — 포트포워딩 불필요)
        │
  Windows 11 PC (서버)
        │  claude --print --dangerously-skip-permissions "..."
        │  gemini --yolo "..."          ← 복수 CLI 동시 실행 가능
        │
        ▼
  스마트폰 Slack 스레드
        ← 결과가 실시간으로 업데이트됩니다
```

**포트포워딩이 필요 없는 이유**: 서버가 Slack 서버에 먼저 WebSocket 연결을 맺고
이벤트를 받아옵니다 (Socket Mode). 공유기 설정을 전혀 건드리지 않아도 됩니다.

---

## 준비물 체크리스트

- [ ] Windows 11 PC (항상 켜 두거나, 사용할 때 켜는 PC)
- [ ] Slack 워크스페이스 (없으면 무료로 생성 가능: https://slack.com)
- [ ] 스마트폰에 Slack 앱 설치
- [ ] Anthropic 계정 (Claude 사용 시): https://console.anthropic.com

---

## PART 1 — Windows 서버 PC 설정

---

### Step 1. Python 설치

1. https://www.python.org/downloads/ 접속
2. **Download Python 3.12.x** 클릭 (3.10 이상이면 모두 가능)
3. 설치 시 **반드시** 아래 옵션 체크

   ```
   ☑ Add python.exe to PATH   ← 이것을 체크하지 않으면 이후 명령어가 동작 안 됨
   ```

4. 설치 완료 후 확인:

   ```powershell
   # 시작 메뉴 → "PowerShell" 검색 → 실행
   python --version
   # 출력 예시: Python 3.12.3
   ```

   > 버전이 출력되지 않으면 PC를 재시작한 뒤 다시 시도합니다.

---

### Step 2. Node.js 설치 (Claude CLI용)

1. https://nodejs.org/ 접속
2. **LTS** 버전 다운로드 및 설치 (기본 옵션 그대로)
3. 설치 후 확인:

   ```powershell
   node --version
   # 출력 예시: v20.11.0

   npm --version
   # 출력 예시: 10.2.4
   ```

---

### Step 3. Claude CLI 설치 및 로그인

```powershell
# Claude CLI 설치
npm install -g @anthropic-ai/claude-code

# 설치 확인
claude --version
# 출력 예시: 1.x.x
```

**로그인 (최초 1회, 반드시 진행)**

```powershell
claude
```

- 터미널에 로그인 안내가 나타나며 브라우저가 자동으로 열립니다
- Anthropic 계정으로 로그인합니다
- 로그인 완료 메시지가 터미널에 뜨면 `Ctrl+C` 로 종료합니다

**로그인 확인:**

```powershell
claude --print --dangerously-skip-permissions "hello"
# 출력 예시: Hello! How can I help you today?
# 위와 같이 응답이 나오면 정상입니다.
```

> ⚠️ 이 로그인 단계를 건너뛰면 서버 실행 시 Claude가 응답하지 않습니다.

---

### Step 4. 프로젝트 다운로드

```powershell
# 원하는 위치로 이동 (예시: C:\Users\user\AI_TOOLS)
cd C:\Users\user
mkdir AI_TOOLS
cd AI_TOOLS

# 저장소 클론
git clone https://github.com/mrjoohk/agent_slack.git
cd agent_slack
```

> Git이 없다면 https://git-scm.com 에서 설치하거나,
> GitHub 페이지에서 **Code → Download ZIP** 으로 다운로드 후 압축 해제합니다.

---

### Step 5. Python 가상환경 및 패키지 설치

```powershell
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 프롬프트 앞에 (.venv) 가 붙으면 성공:
# (.venv) PS C:\Users\user\AI_TOOLS\agent_slack>

# 필요 패키지 설치
pip install slack_bolt websockets pydantic openpyxl
```

---

### Step 6. 작업 디렉토리 생성

```powershell
# AI CLI가 실제로 작업할 폴더 (파일 생성·수정이 여기서 일어남)
mkdir C:\Users\user\AI_Workspace

# 스킬 파일 저장 폴더
mkdir C:\Users\user\AI_Tools\skills\core
```

---

### Step 7. 스킬 파일 작성

스킬(Skill)은 AI에게 미리 전달하는 **시스템 프롬프트 파일**입니다.
`skill[core:claude] 요청` 처럼 사용할 때 `core` 스킬 파일을 읽어 AI에게 전달합니다.

메모장을 열어 아래 내용을 입력하고
`C:\Users\user\AI_Tools\skills\core\SKILL.md` 로 저장합니다.

```markdown
---
name: core
description: 범용 개발 작업
---

당신은 시니어 소프트웨어 엔지니어입니다.
사용자의 요청을 분석하고 코드를 작성하거나 개선합니다.
결과는 항상 한국어로 설명하되, 코드는 영어로 작성하세요.
간결하고 명확한 결과물을 제공하세요.
```

> **스킬 파일 경로 규칙**: `[SKILL_BASE_PATH]\[스킬명]\SKILL.md`
> `core` 스킬 = `C:\Users\user\AI_Tools\skills\core\SKILL.md`

---

### Step 8. 환경변수 파일(.env) 작성

`C:\Users\user\AI_TOOLS\agent_slack` 폴더 안에
`.env` 라는 이름의 파일을 메모장으로 만듭니다.

> 메모장에서 저장할 때: 파일 이름을 `.env` 로, 파일 형식을 **모든 파일** 로 선택합니다.

```env
# ────────────────────────────────────────
# Slack 토큰 (아래 PART 2를 진행한 뒤 붙여넣기)
# ────────────────────────────────────────
# SLACK_BOT_TOKEN  : PART 2 Step 14에서 발급 (xoxb-... 로 시작)
# SLACK_APP_TOKEN  : PART 2 Step 12에서 발급 (xapp-1-... 로 시작)
SLACK_BOT_TOKEN=xoxb-여기에-봇토큰-붙여넣기
SLACK_APP_TOKEN=xapp-1-여기에-앱레벨토큰-붙여넣기

# ────────────────────────────────────────
# CLI 설정
# ────────────────────────────────────────
# skill[name] 처럼 CLI를 지정하지 않을 때 사용할 기본 CLI
DEFAULT_CLI=claude

# ────────────────────────────────────────
# 경로 설정
# ────────────────────────────────────────
SKILL_BASE_PATH=C:\Users\user\AI_Tools\skills
WORKSPACE_PATH=C:\Users\user\AI_Workspace

# 작업 타임아웃 (초) — 이 시간 초과 시 프로세스 강제 종료
JOB_TIMEOUT=300

# ────────────────────────────────────────
# CLI별 API Key (사용하는 CLI에 맞게 주석 해제)
# ────────────────────────────────────────
# GEMINI_API_KEY=AIzaSy...      ← Gemini 사용 시 (없으면 최초 실행 시 브라우저 로그인)
# OPENAI_API_KEY=sk-...         ← Codex 사용 시 (필수)
# CURSOR_AGENT_BIN=cursor       ← Cursor 바이너리 경로 (기본값: cursor)
```

---

### Step 9. 서버 실행 스크립트 만들기

매번 명령어를 타이핑하지 않아도 되도록 배치 파일을 만듭니다.

`C:\Users\user\AI_TOOLS\agent_slack\start_server.bat` 파일을 메모장으로 만들어
아래 내용을 입력하고 저장합니다.

```bat
@echo off
:: 이 배치 파일이 있는 폴더로 이동 (클론 위치와 무관하게 동작)
cd /d "%~dp0"

:: 가상환경 활성화
call .venv\Scripts\activate

:: .env 파일의 환경변수 로드
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /v "^#" .env`) do (
    if not "%%A"=="" if not "%%B"=="" set "%%A=%%B"
)

:: 서버 실행
echo.
echo  AI CLI Bot 시작 중...
echo  Slack 메시지 대기 중 (종료: Ctrl+C)
echo.
python -m ai_cli_relay.app.main

pause
```

---

### Step 10. Slack App 만들기 → PART 2 먼저 진행

**지금은 여기서 멈추고 PART 2(Slack 앱 만들기)를 진행합니다.**
토큰을 발급받은 후 `.env` 파일을 완성하고 서버를 시작합니다.

---

## PART 2 — Slack 앱 생성 및 토큰 발급

> PC 브라우저에서 진행합니다. 약 10분 소요됩니다.

---

### Step 11. Slack App 생성

1. https://api.slack.com/apps 접속 (Slack 계정으로 로그인)
2. 오른쪽 상단 **Create New App** 클릭
3. **From scratch** 선택
4. 설정 입력:
   - **App Name**: `AI-CLI-Bot` (원하는 이름으로 변경 가능)
   - **Pick a workspace**: 사용할 Slack 워크스페이스 선택
5. **Create App** 클릭

---

### Step 12. SLACK_APP_TOKEN 발급 — Socket Mode 활성화

> 이 토큰(`xapp-1-...`)은 서버가 **Slack 서버에 WebSocket으로 연결**할 때 사용합니다.
> 포트포워딩 없이 동작하는 핵심 토큰입니다.

1. 왼쪽 메뉴에서 **Settings** 섹션(아래쪽) → **Socket Mode** 클릭
2. 화면 오른쪽의 **Enable Socket Mode** 토글 클릭 → 초록색 **ON** 상태로 변경

   ```
   Enable Socket Mode  [  ●  ]  ← 이렇게 ON이 되면 됩니다
   ```

3. 팝업 창 **"Generate an app-level token..."** 이 뜨면:
   - **Token Name** 칸에 `socket-token` 입력 (이름은 자유)
   - 아래 **Generate** 버튼 클릭

4. 토큰이 생성됩니다. 아래처럼 `xapp-1-` 로 시작하는 긴 문자열입니다:

   ```
   xapp-1-[워크스페이스ID]-[숫자]-[해시값]
   ```

5. 토큰 오른쪽의 **Copy** 클릭
6. `.env` 파일을 메모장으로 열어 붙여넣기:

   ```env
   SLACK_APP_TOKEN=여기에-xapp-1-로-시작하는-토큰-붙여넣기
   ```

7. **Done** 클릭 → 팝업 닫기

> ⚠️ **지금 바로 `.env`에 붙여넣으세요.** 이 화면을 닫으면 토큰 전체를 다시 볼 수 없습니다.
> (나중에 재발급하려면: 왼쪽 메뉴 **Basic Information** → **App-Level Tokens** 섹션에서 기존 토큰 삭제 후 재생성)

---

### Step 13. Bot 권한(Scopes) 추가

1. 왼쪽 메뉴 **Features** 섹션 → **OAuth & Permissions** 클릭
2. 페이지를 스크롤해서 **Scopes** 섹션 찾기
3. **Bot Token Scopes** 아래 **Add an OAuth Scope** 클릭
4. 아래 6개를 하나씩 검색해서 추가합니다:

   | 추가할 Scope | 용도 |
   |------------|------|
   | `chat:write` | 메시지 전송 |
   | `chat:write.public` | 초대 없이 채널에 메시지 전송 |
   | `channels:history` | 공개 채널 메시지 읽기 |
   | `groups:history` | 비공개 채널 메시지 읽기 |
   | `im:history` | 다이렉트 메시지 읽기 |
   | `mpim:history` | 그룹 DM 메시지 읽기 |

---

### Step 14. SLACK_BOT_TOKEN 발급 — 앱 설치

> 이 토큰(`xoxb-...`)은 봇이 **Slack 채널에 메시지를 보내고 읽을 때** 사용합니다.

1. **OAuth & Permissions** 페이지 맨 위로 스크롤
2. **Install to Workspace** 버튼 클릭

   > 버튼이 보이지 않으면 페이지를 새로고침합니다.

3. Slack 권한 요청 화면이 나타나면 **허용** 클릭
4. 페이지가 새로고침되며 상단에 토큰이 표시됩니다:

   ```
   Bot User OAuth Token
   xoxb-[숫자]-[숫자]-[해시값]    ← xoxb- 로 시작하는 긴 문자열
   [Copy]
   ```

5. **Copy** 클릭
6. `.env` 파일을 메모장으로 열어 붙여넣기:

   ```env
   SLACK_BOT_TOKEN=여기에-xoxb-로-시작하는-토큰-붙여넣기
   ```

> ℹ️ 이 토큰은 **OAuth & Permissions** 페이지에서 언제든지 다시 볼 수 있습니다.
> 유출된 경우 같은 페이지의 **Revoke Token** 으로 무효화하고 재발급합니다.

---

### Step 15. 이벤트 구독 설정

1. 왼쪽 메뉴 **Features** 섹션 → **Event Subscriptions** 클릭
2. **Enable Events** 토글 → **ON**
3. 페이지 아래 **Subscribe to bot events** 클릭
4. **Add Bot User Event** 를 클릭해서 아래 4개 추가:

   | Event 이름 |
   |-----------|
   | `message.channels` |
   | `message.groups` |
   | `message.im` |
   | `message.mpim` |

5. 오른쪽 아래 **Save Changes** 클릭

   > Socket Mode에서는 **Request URL 입력 불필요** — URL 칸은 비워두세요.

---

### Step 16. 앱 재설치 (권한 변경 반영)

이벤트 권한을 추가했으므로 앱을 다시 설치해야 합니다.

1. 왼쪽 메뉴 **Settings** → **Install App** 클릭
2. **Reinstall to Workspace** 클릭 → **허용**

---

## PART 3 — 서버 첫 실행 및 테스트

---

### Step 17. .env 파일 최종 확인

지금까지 입력한 `.env` 파일이 아래처럼 되어 있는지 확인합니다.
(토큰 값은 실제 발급받은 값으로 교체되어 있어야 합니다)

```env
SLACK_BOT_TOKEN=xoxb-실제토큰값
SLACK_APP_TOKEN=xapp-1-실제토큰값
DEFAULT_CLI=claude
SKILL_BASE_PATH=C:\Users\user\AI_Tools\skills
WORKSPACE_PATH=C:\Users\user\AI_Workspace
JOB_TIMEOUT=300
```

---

### Step 18. 서버 실행

`start_server.bat` 파일을 **더블클릭**합니다.

검은 터미널 창이 열리고 아래 메시지가 나오면 **성공**입니다:

```
AI CLI Bot 시작 중...
Slack 메시지 대기 중 (종료: Ctrl+C)

[AI CLI Bot] Socket Mode 시작 — 포트포워딩 불필요, Slack 서버로 아웃바운드 연결
⚡️ Bolt app is running! (Socket Mode)
```

> 오류가 발생하면 아래 **문제 해결** 섹션을 참고합니다.

---

### Step 19. Slack 채널에 봇 초대

Slack 앱(PC 또는 스마트폰)에서:

1. 메시지를 보낼 채널로 이동
2. 채널 메시지 입력창에 아래 입력 후 전송:

   ```
   /invite @AI-CLI-Bot
   ```

   > 봇 이름이 다를 경우 Step 11에서 지은 이름으로 입력합니다.

---

### Step 20. 첫 번째 테스트

채널에서 아래 메시지를 전송합니다:

```
skill[core:claude] 피보나치 수열을 Python으로 구현해줘
```

**정상 동작 시 응답 순서:**

1. 봇이 즉시 스레드에 답변:
   ```
   ⏳ [core | CLAUDE] 작업 시작... (Job: a1b2c3d4)
   > 피보나치 수열을 Python으로 구현해줘
   ```

2. 잠시 후 메시지가 Claude의 실제 응답으로 업데이트:
   ```
   def fibonacci(n):
       if n <= 1:
           return n
       return fibonacci(n-1) + fibonacci(n-2)
   ...
   ```

---

## PART 4 — 스마트폰에서 사용하기

---

### Step 21. 스마트폰에 Slack 설치

- iOS: App Store에서 **Slack** 검색 → 설치
- Android: Play Store에서 **Slack** 검색 → 설치
- 앱 실행 후 PC와 **동일한 Slack 워크스페이스**로 로그인

---

### Step 22. 메시지 보내기

앱 하단 **채널 목록** → 봇을 초대한 채널 선택 → 메시지 입력

```
skill[core:claude] 리스트에서 중복을 제거하는 Python 함수 만들어줘
```

---

## 명령어 사용법 전체 정리

### 기본 형식

```
skill[스킬명:CLI명] 요청 내용
```

### 예시

| 입력 | 설명 |
|------|------|
| `skill[core:claude] 코드 리뷰해줘` | Claude 단독 실행 |
| `skill[core:gemini] 이 함수 최적화해줘` | Gemini 단독 실행 |
| `skill[core:claude,gemini] 두 관점에서 비교해줘` | Claude + Gemini 동시 실행 |
| `skill[core:all] 전부 실행해봐` | Claude, Gemini, Codex, Cursor 동시 실행 |
| `skill[core] 빠르게 해줘` | 기본 CLI(DEFAULT_CLI) 사용 |

### 복수 CLI 실행 시 Slack 스레드 구조

```
내 메시지: skill[core:claude,gemini] 비교해줘

봇: 🚀 [core] `claude, gemini` 2개 CLI에 요청을 분배합니다.
  └▶ ⏳ [core | CLAUDE] 작업 시작...   → Claude 결과 실시간 업데이트
  └▶ ⏳ [core | GEMINI]  작업 시작...  → Gemini 결과 실시간 업데이트 (동시)
```

---

## 문제 해결

### ❌ start_server.bat 실행 시 창이 바로 닫힘

원인: Python 오류 또는 환경변수 미설정

해결: PowerShell에서 직접 실행하면 오류 메시지를 볼 수 있습니다.

```powershell
cd C:\Users\user\AI_TOOLS\agent_slack
.venv\Scripts\activate
# .env 내용을 직접 PowerShell에 붙여넣기 (set 명령어 사용)
set SLACK_BOT_TOKEN=xoxb-...
set SLACK_APP_TOKEN=xapp-...
set DEFAULT_CLI=claude
set SKILL_BASE_PATH=C:\Users\user\AI_Tools\skills
set WORKSPACE_PATH=C:\Users\user\AI_Workspace
set JOB_TIMEOUT=300
python -m ai_cli_relay.app.main
```

---

### ❌ "SLACK_BOT_TOKEN" 오류

`.env` 파일의 토큰 값이 더미 텍스트 그대로입니다.
PART 2를 다시 따라하며 실제 토큰을 입력합니다.

---

### ❌ 봇이 메시지에 반응하지 않음

순서대로 확인합니다:

1. 서버 터미널 창이 열려 있고 `Bolt app is running!` 메시지가 있는가?
2. Slack 채널에 봇이 초대되어 있는가? (`/invite @봇이름`)
3. 메시지 형식이 정확한가? → `skill[스킬명:CLI명] 내용`
4. 서버 터미널에 수신 로그가 찍히는가?

---

### ❌ `⏳` 메시지는 오는데 결과가 업데이트 안 됨

원인: Claude CLI 로그인이 안 된 상태

해결:
```powershell
claude --print --dangerously-skip-permissions "hello"
```
응답이 없으면 `claude` 를 실행해서 브라우저 로그인을 다시 합니다.

---

### ❌ `FileNotFoundError: Skill 'core' not found`

`C:\Users\user\AI_Tools\skills\core\SKILL.md` 파일이 없습니다.
Step 7을 다시 진행합니다.

---

### ❌ 터미널 창을 닫으면 봇이 멈춤

PC를 재시작해도 자동으로 봇이 켜지려면 **Windows 작업 스케줄러**를 사용합니다.

1. `Win + S` → **작업 스케줄러** 검색 → 실행
2. 오른쪽 **작업 만들기** 클릭
3. **일반** 탭:
   - 이름: `AI CLI Slack Bot`
   - **로그온 여부에 관계없이 실행** 선택
   - **가장 높은 수준의 권한으로 실행** 체크
4. **트리거** 탭 → 새로 만들기 → **시스템 시작 시**
5. **동작** 탭 → 새로 만들기:
   - 프로그램: `C:\Users\user\AI_TOOLS\agent_slack\start_server.bat`
   - 시작 위치: `C:\Users\user\AI_TOOLS\agent_slack`
6. **확인** → 암호 입력 → 저장

---

## 환경변수 전체 목록

| 변수 | 필수 | 설명 | 예시 |
|------|:----:|------|------|
| `SLACK_BOT_TOKEN` | ✅ | Slack Bot OAuth Token | `xoxb-...` |
| `SLACK_APP_TOKEN` | ✅ | Socket Mode App-Level Token | `xapp-1-...` |
| `DEFAULT_CLI` | | CLI 미지정 시 사용할 기본값 | `claude` |
| `SKILL_BASE_PATH` | | 스킬 파일 루트 경로 | `C:\Users\user\AI_Tools\skills` |
| `WORKSPACE_PATH` | | CLI 작업 디렉토리 | `C:\Users\user\AI_Workspace` |
| `JOB_TIMEOUT` | | 작업 타임아웃(초) | `300` |
| `GEMINI_API_KEY` | | Gemini CLI 사용 시 | `AIzaSy...` |
| `OPENAI_API_KEY` | | Codex CLI 사용 시 | `sk-...` |
| `CURSOR_AGENT_BIN` | | Cursor 바이너리 경로 | `cursor` |
