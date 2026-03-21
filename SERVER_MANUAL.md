# 서버 PC 운영 매뉴얼

> 이 문서는 Slack Bot 릴레이 서버로 사용하는 **Windows 11 PC에서 해야 할
> 모든 작업**을 다룹니다. 최초 1회 설정부터 서버 기동, 자동 시작, 유지보수까지
> 순서대로 따라 하면 됩니다.

---

## 목차

1. [최초 1회 설정](#1-최초-1회-설정)
2. [CLI별 설치 및 인증](#2-cli별-설치-및-인증)
3. [서버 수동 실행](#3-서버-수동-실행)
4. [Windows 부팅 시 자동 시작 설정](#4-windows-부팅-시-자동-시작-설정)
5. [CLI 인증 확인 및 갱신](#5-cli-인증-확인-및-갱신)
6. [서버 상태 확인 및 재시작](#6-서버-상태-확인-및-재시작)
7. [스킬 추가 및 관리](#7-스킬-추가-및-관리)
8. [로그 확인](#8-로그-확인)
9. [업데이트 절차](#9-업데이트-절차)
10. [문제 해결 체크리스트](#10-문제-해결-체크리스트)

---

## 1. 최초 1회 설정

> **PC 교체나 재설치 시 이 섹션을 처음부터 다시 진행합니다.**

### 1-1. 소프트웨어 설치 확인

PowerShell에서 아래 명령어로 버전을 확인합니다.

```powershell
python --version     # 3.10 이상 필요
node --version       # v18 이상 필요 (Claude CLI용)
npm --version
git --version
```

없는 항목은 설치:
- Python: https://python.org/downloads → "Add to PATH" 반드시 체크
- Node.js: https://nodejs.org → LTS 버전

### 1-2. Claude CLI 설치 및 인증 ★ 가장 중요

```powershell
# 설치
npm install -g @anthropic-ai/claude-code

# 설치 확인
claude --version
```

**인증 (반드시 대화형으로 1회 진행)**

```powershell
claude
```

처음 실행 시 브라우저가 열리며 Anthropic 계정 로그인 화면이 나타납니다.
로그인 후 터미널로 돌아오면 인증 완료입니다.

> **왜 이 단계가 중요한가?**
> 서버 모드(`--print --dangerously-skip-permissions`)로 실행할 때
> 인증 정보가 없으면 프로세스가 로그인 요청 화면에서 멈춥니다.
> **최초 1회는 반드시 대화형으로 인증해야 합니다.**

인증 상태 확인:

```powershell
claude --print "hello"
# "Hello!" 같은 응답이 출력되면 정상
```

### 1-3. 프로젝트 클론 및 패키지 설치

```powershell
# 원하는 위치에 클론
cd C:\Users\user\AI_TOOLS
git clone https://github.com/mrjoohk/agent_slack.git
cd agent_slack

# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate

# 패키지 설치
pip install slack_bolt websockets pydantic openpyxl
```

### 1-4. 디렉토리 구조 생성

```powershell
# 스킬 저장 디렉토리
mkdir "C:\Users\user\.gemini\antigravity\skills"

# 스킬 예시 — core 스킬 생성
mkdir "C:\Users\user\.gemini\antigravity\skills\core"

# CLI 작업 공간
mkdir "C:\Users\user\workspace"
```

### 1-5. .env 파일 작성

`C:\Users\user\AI_TOOLS\agent_slack\.env` 파일을 메모장으로 생성:

```env
SLACK_BOT_TOKEN=xoxb-여기에-봇토큰-붙여넣기
SLACK_APP_TOKEN=xapp-1-여기에-앱레벨토큰-붙여넣기

# 사용할 CLI 선택: claude | gemini | codex | cursor
SELECTED_CLI=claude

SKILL_BASE_PATH=C:\Users\user\.gemini\antigravity\skills
WORKSPACE_PATH=C:\Users\user\workspace
JOB_TIMEOUT=300

# CLI별 API Key (사용하는 CLI에 맞게 추가)
# GEMINI_API_KEY=AIzaSy...         # Gemini 사용 시 (없으면 브라우저 인증)
# OPENAI_API_KEY=sk-...            # Codex 사용 시 (필수)
# CURSOR_AGENT_BIN=cursor          # Cursor 바이너리 경로 (기본값: cursor)
```

> Slack 토큰 발급 방법은 SETUP_MANUAL.md 4단계를 참고하세요.

### 1-6. 기본 스킬 파일 작성

`C:\Users\user\.gemini\antigravity\skills\core\SKILL.md` 파일 생성:

```markdown
---
name: core
description: 범용 개발 작업
---

당신은 시니어 소프트웨어 엔지니어입니다.
사용자의 요청을 분석하고 코드를 작성하거나 개선합니다.
결과는 항상 한국어로 설명하되, 코드는 영어로 작성하세요.
```

### 1-7. 서버 최초 실행 테스트

```powershell
cd C:\Users\user\AI_TOOLS\agent_slack

# 환경변수 로드
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# 가상환경 활성화
.venv\Scripts\activate

# 서버 실행
python -m ai_cli_relay.app.main
```

아래 메시지가 나오면 성공:

```
[AI CLI Bot] Socket Mode 시작 — 포트포워딩 불필요, Slack 서버로 아웃바운드 연결
⚡️ Bolt app is running! (Socket Mode)
```

---

---

## 2. CLI별 설치 및 인증

> 사용할 CLI 하나만 설치하면 됩니다. `SELECTED_CLI` 환경변수로 선택합니다.

---

### 2-A. Claude Code CLI (기본값, `SELECTED_CLI=claude`)

```powershell
# 설치
npm install -g @anthropic-ai/claude-code

# 인증 — 최초 1회 대화형으로 진행 (브라우저 Anthropic 계정 로그인)
claude
# 로그인 완료 후 Ctrl+C

# 서버 모드 동작 확인
claude --print --dangerously-skip-permissions "hello"
# 응답 텍스트가 출력되면 정상
```

**서버 모드 플래그**: `--print --dangerously-skip-permissions`
- `--print`: 비대화식 출력 후 종료
- `--dangerously-skip-permissions`: 파일 읽기·쓰기·명령 실행 권한 확인 생략

**인증 정보 저장 위치**: `%APPDATA%\Claude\` (Windows)
인증 만료 시 서버를 중단하고 `claude` 재실행 후 브라우저 로그인.

---

### 2-B. Gemini CLI (`SELECTED_CLI=gemini`)

```powershell
# 설치
npm install -g @google/gemini-cli

# 인증 방법 1 — 브라우저 Google 계정 로그인 (최초 1회)
gemini
# 브라우저가 열리면 Google 계정으로 로그인 후 터미널로 복귀

# 인증 방법 2 — API Key (서버 환경 권장)
# Google AI Studio(https://aistudio.google.com)에서 API Key 발급 후 .env에 추가:
# GEMINI_API_KEY=AIzaSy...
```

`.env`에 추가:
```env
SELECTED_CLI=gemini
GEMINI_API_KEY=AIzaSy...   # API Key 인증 사용 시
```

**서버 모드 동작 확인**:
```powershell
gemini --yolo "hello"
# 응답 텍스트가 출력되면 정상
```

**서버 모드 플래그**: `--yolo`
- 모든 도구 실행 및 파일 변경을 자동 승인

---

### 2-C. OpenAI Codex CLI (`SELECTED_CLI=codex`)

```powershell
# 설치
npm install -g @openai/codex

# 인증 — API Key 방식 (대화형 로그인 없음)
# OpenAI Platform(https://platform.openai.com/api-keys)에서 API Key 발급
```

`.env`에 추가:
```env
SELECTED_CLI=codex
OPENAI_API_KEY=sk-...
```

**서버 모드 동작 확인**:
```powershell
codex --approval-mode full-auto "hello"
# 응답 텍스트가 출력되면 정상
```

**서버 모드 플래그**: `--approval-mode full-auto`
- 모든 파일 변경 및 명령 실행을 자동 승인

---

### 2-D. Cursor Agent CLI (`SELECTED_CLI=cursor`)

```powershell
# Cursor IDE 설치 (https://www.cursor.com/downloads)
# 설치 후 PATH에 cursor 바이너리가 등록되어 있는지 확인
cursor --version
```

**바이너리 경로 확인**:
Cursor 버전 및 설치 방식에 따라 바이너리 경로가 다릅니다.
경로를 직접 확인해서 `.env`에 명시하는 것을 권장합니다.

```powershell
# 바이너리 위치 탐색
where cursor
# 또는
Get-Command cursor | Select-Object Source
```

`.env`에 추가:
```env
SELECTED_CLI=cursor
CURSOR_AGENT_BIN=cursor          # 기본값. 경로가 다르면 전체 경로 입력
                                  # 예: C:\Users\user\AppData\Local\Programs\cursor\cursor.exe
```

**인증**: Cursor IDE에 로그인한 상태여야 CLI도 인증됩니다.
Cursor IDE를 열어서 계정 로그인 확인 후 사용하세요.

> ⚠️ **주의**: Cursor의 CLI agent 기능은 버전에 따라 플래그·동작이 다를 수 있습니다.
> 실제 실행 전 `cursor agent --help`로 지원 플래그를 확인하세요.
> 문제가 있으면 `CURSOR_AGENT_BIN` 환경변수로 정확한 바이너리 경로를 지정합니다.

---

### CLI별 비교 요약

| CLI | 설치 패키지 | 인증 방식 | 서버 모드 플래그 | 추가 env var |
|-----|-----------|---------|--------------|------------|
| Claude | `@anthropic-ai/claude-code` | 브라우저 1회 로그인 | `--print --dangerously-skip-permissions` | 없음 |
| Gemini | `@google/gemini-cli` | 브라우저 or API Key | `--yolo` | `GEMINI_API_KEY` (선택) |
| Codex | `@openai/codex` | API Key | `--approval-mode full-auto` | `OPENAI_API_KEY` (필수) |
| Cursor | Cursor IDE 설치 | IDE 로그인 | `agent --no-confirm` | `CURSOR_AGENT_BIN` (선택) |

---

## 3. 서버 수동 실행

매번 서버를 시작할 때 사용하는 명령어 모음입니다.

### 3-1. start_server.bat 스크립트 생성 (권장)

반복 입력을 줄이기 위해 배치 파일을 하나 만들어 두면 편리합니다.

`C:\Users\user\AI_TOOLS\agent_slack\start_server.bat` 파일 생성:

```bat
@echo off
cd /d C:\Users\user\AI_TOOLS\agent_slack

:: 가상환경 활성화
call .venv\Scripts\activate

:: .env 환경변수 로드
for /f "tokens=1,* delims==" %%A in ('findstr /v "^#" .env') do (
    set "%%A=%%B"
)

:: 서버 실행
echo [AI CLI Bot] 서버를 시작합니다...
python -m ai_cli_relay.app.main

pause
```

이후 서버 시작은 이 파일을 더블클릭하면 됩니다.

---

## 4. Windows 부팅 시 자동 시작 설정

PC를 재시작해도 서버가 자동으로 켜지게 합니다.

### 방법 A — 시작 프로그램 폴더 등록 (가장 간단)

1. `Win + R` → `shell:startup` 입력 → 엔터
2. 열린 폴더에 `start_server.bat` 파일의 **바로가기**를 복사
3. 다음 부팅부터 자동 실행

> 단점: 터미널 창이 화면에 표시됨. 창을 닫으면 서버가 종료됨.

### 방법 B — 작업 스케줄러 (로그인 없이 백그라운드 실행, 권장)

1. `Win + S` → **작업 스케줄러** 검색 → 실행
2. 오른쪽 **작업 만들기** 클릭

**일반 탭:**
- 이름: `AI CLI Slack Bot`
- **로그온 여부에 관계없이 실행** 선택
- **가장 높은 수준의 권한으로 실행** 체크

**트리거 탭:**
- 새로 만들기 → 작업 시작: **시스템 시작 시**

**동작 탭:**
- 새로 만들기
- 프로그램/스크립트: `C:\Users\user\AI_TOOLS\agent_slack\start_server.bat`
- 시작 위치: `C:\Users\user\AI_TOOLS\agent_slack`

**설정 탭:**
- **작업이 이미 실행 중이면: 새 인스턴스를 시작하지 않음** 선택

3. 확인 → Windows 암호 입력 → 저장

**등록 후 테스트:**

```powershell
# 작업 스케줄러에서 방금 만든 작업 우클릭 → 실행
# 또는 PowerShell에서:
Start-ScheduledTask -TaskName "AI CLI Slack Bot"
```

---

## 5. CLI 인증 확인 및 갱신

Claude CLI 인증은 세션 기반으로, 장기간 미사용 시 만료될 수 있습니다.

### 인증 상태 확인

사용 중인 CLI에 맞는 명령어로 확인합니다.

```powershell
# Claude
claude --print --dangerously-skip-permissions "ping"

# Gemini
gemini --yolo "ping"

# Codex (OPENAI_API_KEY가 환경변수에 있어야 함)
codex --approval-mode full-auto "ping"

# 정상: 응답 텍스트 출력
# 인증 문제: 로그인 안내 메시지 또는 즉시 오류 종료
```

### 인증 만료 시 갱신

서버를 일시 중단하고 대화형으로 재인증합니다.

```powershell
# 서버 종료
Stop-ScheduledTask -TaskName "AI CLI Slack Bot"

# CLI별 재인증
# Claude: 브라우저 로그인
claude

# Gemini: 브라우저 로그인
gemini
# (또는 .env의 GEMINI_API_KEY 갱신)

# Codex: .env의 OPENAI_API_KEY 갱신 (API Key는 만료 없음, 단 취소 시 교체 필요)

# Cursor: Cursor IDE 열어서 재로그인

# 서버 재시작
Start-ScheduledTask -TaskName "AI CLI Slack Bot"
```

> **팁**: 서버가 갑자기 응답하지 않으면 가장 먼저 인증 만료를 의심하세요.
> Slack 스레드에 `❌ 오류 발생` 메시지가 반복되면 이 절차를 실행합니다.

---

## 6. 서버 상태 확인 및 재시작

### 실행 중인 프로세스 확인

```powershell
# Python 프로세스 목록
Get-Process python | Select-Object Id, CPU, WorkingSet, StartTime

# 특정 포트 점유 확인 (사용하지 않지만 혹시 모를 경우)
netstat -ano | findstr :8000
```

### 서버 재시작

```powershell
# 실행 중인 Python 프로세스 종료
Get-Process python | Stop-Process -Force

# 재시작 (배치 파일)
Start-Process "C:\Users\user\AI_TOOLS\agent_slack\start_server.bat"

# 또는 작업 스케줄러 사용 시
Stop-ScheduledTask -TaskName "AI CLI Slack Bot"
Start-ScheduledTask -TaskName "AI CLI Slack Bot"
```

---

## 7. 스킬 추가 및 관리

### 새 스킬 추가

```powershell
# 1. 스킬 폴더 생성
mkdir "C:\Users\user\.gemini\antigravity\skills\새스킬명"

# 2. SKILL.md 작성 (메모장 또는 VSCode로)
notepad "C:\Users\user\.gemini\antigravity\skills\새스킬명\SKILL.md"
```

SKILL.md 기본 템플릿:

```markdown
---
name: 새스킬명
description: 스킬 설명
---

[여기에 AI에게 전달할 시스템 프롬프트 작성]
```

### 스킬 목록 확인

```powershell
Get-ChildItem "C:\Users\user\.gemini\antigravity\skills" -Directory | Select-Object Name
```

### 스킬 수정

수정 후 **서버 재시작 없이** 즉시 반영됩니다.
(요청이 들어올 때마다 파일을 읽으므로 핫 리로드가 자동으로 됩니다.)

---

## 8. 로그 확인

현재 서버는 콘솔 출력(`print`)으로 로그를 남깁니다.

### 실시간 로그 (배치 파일 실행 시)

서버 창에서 바로 확인 가능:

```
[a1b2c3d4] Worker started | skill=core | cli=claude
[a1b2c3d4] Spawned PID: 12345
[a1b2c3d4] Pipeline finished
```

### 로그를 파일로 저장 (권장)

`start_server.bat`의 마지막 실행 줄을 아래와 같이 변경:

```bat
python -m ai_cli_relay.app.main >> logs\server.log 2>&1
```

로그 디렉토리 생성:

```powershell
mkdir "C:\Users\user\AI_TOOLS\agent_slack\logs"
```

이후 로그 확인:

```powershell
# 최근 50줄 실시간 확인
Get-Content logs\server.log -Tail 50 -Wait
```

---

## 9. 업데이트 절차

코드가 GitHub에 새로 올라왔을 때 서버를 업데이트합니다.

```powershell
# 1. 서버 중단
Stop-ScheduledTask -TaskName "AI CLI Slack Bot"
# 또는: Get-Process python | Stop-Process -Force

# 2. 최신 코드 받기
cd C:\Users\user\AI_TOOLS\agent_slack
git pull origin master

# 3. 패키지 업데이트 (필요한 경우)
.venv\Scripts\activate
pip install -r ai_cli_relay/requirements.txt

# 4. 서버 재시작
Start-ScheduledTask -TaskName "AI CLI Slack Bot"
# 또는: start_server.bat 더블클릭
```

---

## 10. 문제 해결 체크리스트

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| Slack 봇 응답 없음 | 서버 미실행 | `Get-Process python` 확인, 서버 재시작 |
| Slack 봇 응답 없음 | Socket Mode 연결 끊김 | 서버 재시작, `SLACK_APP_TOKEN` 확인 |
| `❌ 오류 발생` 반복 (Claude) | Claude CLI 인증 만료 | `claude` 재실행 → 브라우저 로그인 |
| `❌ 오류 발생` 반복 (Gemini) | Gemini 인증 만료 or API Key 없음 | `gemini` 재실행 or `.env`의 `GEMINI_API_KEY` 확인 |
| `❌ 오류 발생` 반복 (Codex) | `OPENAI_API_KEY` 미설정 or 잘못됨 | `.env`의 `OPENAI_API_KEY` 확인 |
| `❌ 오류 발생` 반복 (Cursor) | Cursor 바이너리 경로 오류 | `where cursor` 확인 후 `CURSOR_AGENT_BIN` 설정 |
| `❌ 오류 발생` + PID 없음 | CLI 명령어를 찾을 수 없음 | `claude --version` 등으로 설치 확인, npm 재설치 |
| `FileNotFoundError: Skill 'xxx'` | 스킬 파일 없음 | 7단계 스킬 생성 절차 확인 |
| 요청 후 5분간 무응답 | 타임아웃 (`JOB_TIMEOUT=300`) | `.env`에서 `JOB_TIMEOUT` 값 늘리기 |
| PC 재시작 후 봇 미동작 | 자동 시작 미설정 | 4단계 자동 시작 설정 확인 |
| `.env` 환경변수 미적용 | 로드 명령어 미실행 | `start_server.bat` 사용 확인 |

---

## 서버 PC 상태 한눈에 점검

아래 명령어를 PowerShell에서 순서대로 실행하면 전체 상태를 30초 안에 확인할 수 있습니다.

```powershell
# 1. Python 서버 실행 중?
Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, CPU

# 2. Claude CLI 동작?
claude --print "test" 2>&1 | Select-Object -First 1

# 3. 스킬 목록
Get-ChildItem "C:\Users\user\.gemini\antigravity\skills" -Directory | Select-Object Name

# 4. 작업 공간 존재?
Test-Path "C:\Users\user\workspace"

# 5. .env 환경변수 로드됐는지 확인
echo "BOT_TOKEN: $env:SLACK_BOT_TOKEN" | Select-Object -First 1
```
