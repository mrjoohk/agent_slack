import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec


class GeminiCLIAdapter(BaseCLIAdapter):
    """
    Google Gemini CLI (@google/gemini-cli) 서브프로세스 래퍼.

    설치:  npm install -g @google/gemini-cli
    인증:  아래 둘 중 하나 선택
           1) 최초 1회 `gemini` 실행 → 브라우저에서 Google 계정 로그인
           2) GEMINI_API_KEY 환경변수 설정 (Google AI Studio에서 발급)
    """

    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        # --yolo : 모든 도구 실행 및 파일 변경을 자동 승인 (서버 무인 실행 필수)
        # GEMINI_API_KEY가 환경변수에 있으면 브라우저 인증 없이 동작
        # Windows: npm 설치 CLI는 .cmd 래퍼이므로 cmd /c 를 통해 실행
        cmd = ["cmd", "/c", "gemini", "--yolo", spec.prompt]
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
