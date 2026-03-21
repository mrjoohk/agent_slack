@echo off
:: 이 배치 파일이 있는 폴더로 이동 (클론 위치와 무관하게 동작)
cd /d "%~dp0"

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
