@echo off
cd /d "%~dp0"

call .venv\Scripts\activate

for /f "tokens=1,* delims==" %%A in ('findstr /v "^#" .env') do (
    set "%%A=%%B"
)

set PYTHONUTF8=1
echo [AI CLI Bot] Starting server...
python -m ai_cli_relay.app.main

pause
