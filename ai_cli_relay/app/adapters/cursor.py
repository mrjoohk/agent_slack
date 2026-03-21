import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec


class CursorCLIAdapter(BaseCLIAdapter):
    """
    Cursor Background Agent CLI 서브프로세스 래퍼.

    설치:  Cursor IDE 설치 후 PATH에 cursor 바이너리 추가
           https://www.cursor.com/downloads
    인증:  Cursor IDE에서 계정 로그인 상태 유지 (세션이 CLI와 공유됨)

    바이너리 설정:
        기본값은 환경변수 CURSOR_AGENT_BIN 으로 재정의 가능.
        예: CURSOR_AGENT_BIN=C:\\path\\to\\cursor.exe
        Cursor 버전에 따라 바이너리명·플래그가 달라질 수 있으므로
        실제 설치 경로를 확인 후 .env에 명시하는 것을 권장.
    """

    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        # CURSOR_AGENT_BIN: 바이너리 경로를 환경변수로 재정의 가능 (기본: "cursor")
        binary = os.environ.get("CURSOR_AGENT_BIN", "cursor")

        # --no-confirm : 파일 변경·명령 실행 시 확인 프롬프트 생략 (서버 무인 실행 필수)
        # Cursor 버전에 따라 플래그가 다를 수 있음 — 동작 확인 후 조정 필요
        cmd = [binary, "agent", "--no-confirm", spec.prompt]
        cwd = spec.workspace_path if os.path.exists(spec.workspace_path) else str(Path.home())

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env={**os.environ, **spec.env_vars}
        )
        return str(self.process.pid)

    async def stream(self, job_id: str) -> AsyncGenerator[str, None]:
        if not self.process or not self.process.stdout:
            yield "Process not found or failed to start.\n"
            return

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            yield line.decode('utf-8', errors='replace')

        await self.process.wait()

    async def status(self, job_id: str) -> str:
        if not self.process:
            return "NOT_STARTED"
        if self.process.returncode is None:
            return "RUNNING"
        return "COMPLETED" if self.process.returncode == 0 else "FAILED"

    async def cancel(self, job_id: str) -> bool:
        if self.process and self.process.returncode is None:
            self.process.terminate()
            return True
        return False
