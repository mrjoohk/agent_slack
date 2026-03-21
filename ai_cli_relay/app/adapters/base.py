from abc import ABC, abstractmethod
from typing import AsyncGenerator
import pydantic

class JobSpec(pydantic.BaseModel):
    job_id: str
    skill_name: str
    prompt: str
    workspace_path: str
    env_vars: dict = {}

class BaseCLIAdapter(ABC):
    """
    모든 AI CLI Worker (Cursor, Claude, Gemini, Codex 등)이
    상속받아 구현해야 하는 기본 인터페이스 (IF-04)
    """

    @abstractmethod
    async def submit(self, spec: JobSpec) -> str:
        """
        CLI 명령어를 생성하고 백그라운드 프로세스(혹은 Docker 컨테이너)에 제출합니다.
        
        Returns:
            str: 내부 컨테이너 ID 또는 프로세스 ID
        """
        pass

    @abstractmethod
    async def stream(self, job_id: str) -> AsyncGenerator[str, None]:
        """
        할당된 CLI 도구의 표준 출력(stdout/stderr)을 비동기 제너레이터로 반환합니다.
        이 제너레이터의 결과물은 Slack Message Updater (Debounce) 로 흘러갑니다.
        """
        pass

    @abstractmethod
    async def status(self, job_id: str) -> str:
        """
        작업의 현재 상태를 반환합니다.
        (예: RUNNING, COMPLETED, FAILED)
        """
        pass

    @abstractmethod
    async def cancel(self, job_id: str) -> bool:
        """
        강제로 작업을 종료(kill/suspend) 시키는 로직
        """
        pass
