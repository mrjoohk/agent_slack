import asyncio
import os
from typing import AsyncGenerator
from .base import BaseCLIAdapter, JobSpec

class ClaudeCLIAdapter(BaseCLIAdapter):
    """
    Claude CLI (npm claude-code)의 서브프로세스 래퍼 구현체
    """
    def __init__(self):
        self.process = None

    async def submit(self, spec: JobSpec) -> str:
        """
        claude CLI를 서브프로세스로 실행
        """
        # 실행 인자 설정 (예: claude --print "프롬프트")
        cmd = ["claude", "--print", spec.prompt]
        
        # 워크스페이스 타겟 경로 확인
        cwd = spec.workspace_path if os.path.exists(spec.workspace_path) else "/app/workspace"

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # stderr를 stdout으로 병합
            cwd=cwd,
            env={**os.environ, **spec.env_vars}
        )
        
        return str(self.process.pid)

    async def stream(self, job_id: str) -> AsyncGenerator[str, None]:
        if not self.process or not self.process.stdout:
            yield "Process not found or not started properly.\n"
            return
            
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            # 줄 단위로 읽은 것을 제너레이터로 yield
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
