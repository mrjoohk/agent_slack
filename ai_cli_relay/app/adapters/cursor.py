import asyncio
import os
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec

class CursorCLIAdapter(BaseCLIAdapter):
    """
    Cursor 전용 어댑터.
    사용자의 요청에 따라 실행 커맨드를 'agent'로 매핑.
    """
    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        # Cursor CLI 구동: 사용자가 별도 지시한 'agent' 바이너리명 사용
        cmd = ["agent", spec.prompt]
        cwd = spec.workspace_path if os.path.exists(spec.workspace_path) else "/app/workspace"

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
