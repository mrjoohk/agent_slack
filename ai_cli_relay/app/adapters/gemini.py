import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec

class GeminiCLIAdapter(BaseCLIAdapter):
    """
    Gemini CLI를 샌드박스 내부에서 캡처하는 어댑터
    """
    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        # shell=False 로 배열로 처리되어 Command Injection 차단됨
        cmd = ["gemini", "prompt", spec.prompt]
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
