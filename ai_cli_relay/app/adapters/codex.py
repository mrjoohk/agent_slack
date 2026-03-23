import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec


class CodexCLIAdapter(BaseCLIAdapter):
    """
    OpenAI Codex CLI (@openai/codex) 서브프로세스 래퍼.

    설치:  npm install -g @openai/codex
    인증:  OPENAI_API_KEY 환경변수 설정 (대화형 로그인 없음)
           .env 파일에 OPENAI_API_KEY=sk-... 추가
    """

    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        # --approval-mode full-auto : 모든 파일 변경·명령 실행을 자동 승인 (서버 무인 실행 필수)
        # OPENAI_API_KEY 환경변수가 없으면 즉시 오류로 종료됨
        # Windows: npm 설치 CLI는 .cmd 래퍼이므로 cmd /c 를 통해 실행
        cmd = ["cmd", "/c", "codex", "--approval-mode", "full-auto", spec.prompt]
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
            yield "Process not found.\n"
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
