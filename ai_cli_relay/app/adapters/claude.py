import asyncio
import os
from pathlib import Path
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
        # --print: 비대화식 출력 후 종료
        # --dangerously-skip-permissions: 서버 무인 실행 시 권한 확인 프롬프트 생략
        #   (개인 서버에서 자동 실행 목적으로만 사용할 것)
        cmd = ["claude", "--print", "--dangerously-skip-permissions", spec.prompt]

        # 워크스페이스 경로 확인 (없으면 홈 디렉토리로 폴백 - Windows/Linux 모두 안전)
        cwd = spec.workspace_path if os.path.exists(spec.workspace_path) else str(Path.home())

        # CLAUDECODE 환경변수 제거: Claude Code는 중첩 세션을 차단함.
        # 서버가 Claude Code(VSCode 확장 등) 안에서 실행될 때 이 변수가 설정되어 있으면
        # 서브프로세스로 claude CLI를 실행할 수 없으므로 제거 후 전달.
        child_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        child_env.update(spec.env_vars)

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # stderr를 stdout으로 병합
            cwd=cwd,
            env=child_env,
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
