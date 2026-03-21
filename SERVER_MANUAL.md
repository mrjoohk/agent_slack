# 서버 PC 운영 매뉴얼

> 이 문서는 Slack Bot 릴레이 서버로 사용하는 **Windows 11 PC에서 해야 할
> 모든 작업**을 다룹니다. 최초 1회 설정부터 서버 기동, 자동 시작, 유지보수까지
> 순서대로 따라 하면 됩니다.

---

## 목차

1. [최초 1회 설정](#1-최초-1회-설정)
2. [서버 수동 실행](#2-서버-수동-실행)
3. [Windows 부팅 시 자동 시작 설정](#3-windows-부팅-시-자동-시작-설정)
4. [Claude CLI 인증 확인 및 갱신](#4-claude-cli-인증-확인-및-갱신)
5. [서버 상태 확인 및 재시작](#5-서버-상태-확인-및-재시작)
6. [스킬 추가 및 관리](#6-스킬-추가-및-관리)
7. [로그 확인](#7-로그-확인)
8. [업데이트 절차](#8-업데이트-절차)
9. [문제 해결 체크리스트](#9-문제-해결-체크리스트)

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
SELECTED_CLI=claude
SKILL_BASE_PATH=C:\Users\user\.gemini\antigravity\skills
WORKSPACE_PATH=C:\Users\user\workspace
JOB_TIMEOUT=300
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

## 2. 서버 수동 실행

매번 서버를 시작할 때 사용하는 명령어 모음입니다.

### start_server.bat 스크립트 생성 (권장)

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

## 3. Windows 부팅 시 자동 시작 설정

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

## 4. Claude CLI 인증 확인 및 갱신

Claude CLI 인증은 세션 기반으로, 장기간 미사용 시 만료될 수 있습니다.

### 인증 상태 확인

```powershell
claude --print "ping"
# 정상: 응답 텍스트 출력
# 만료: 로그인 안내 메시지 또는 오류
```

### 인증 만료 시 갱신

서버를 일시 중단하고 대화형으로 재인증합니다.

```powershell
# 서버 종료 (작업 스케줄러로 실행 중인 경우)
Stop-ScheduledTask -TaskName "AI CLI Slack Bot"

# 재인증 (브라우저 로그인)
claude
# 로그인 완료 후 Ctrl+C로 종료

# 서버 재시작
Start-ScheduledTask -TaskName "AI CLI Slack Bot"
```

> **팁**: 서버가 갑자기 응답하지 않으면 가장 먼저 인증 만료를 의심하세요.
> Slack 스레드에 `❌ 오류 발생` 메시지가 반복되면 이 절차를 실행합니다.

---

## 5. 서버 상태 확인 및 재시작

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

## 6. 스킬 추가 및 관리

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

## 7. 로그 확인

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

## 8. 업데이트 절차

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

## 9. 문제 해결 체크리스트

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| Slack 봇 응답 없음 | 서버 미실행 | `Get-Process python` 확인, 서버 재시작 |
| Slack 봇 응답 없음 | Socket Mode 연결 끊김 | 서버 재시작, `SLACK_APP_TOKEN` 확인 |
| `❌ 오류 발생` 반복 | Claude CLI 인증 만료 | 4단계 인증 갱신 절차 실행 |
| `❌ 오류 발생` + PID 없음 | `claude` 명령어 못 찾음 | `claude --version` 확인, npm 재설치 |
| `FileNotFoundError: Skill 'xxx'` | 스킬 파일 없음 | 6단계 스킬 생성 절차 확인 |
| 요청 후 5분간 무응답 | 타임아웃 (`JOB_TIMEOUT=300`) | `.env`에서 `JOB_TIMEOUT` 값 늘리기 |
| PC 재시작 후 봇 미동작 | 자동 시작 미설정 | 3단계 자동 시작 설정 확인 |
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
