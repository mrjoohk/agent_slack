import asyncio
from typing import Dict, Any
from .skill_loader import SkillLoader
from ..adapters.claude import ClaudeCLIAdapter, JobSpec
from ..bot.slack_throttler import SlackThrottler

async def run_langgraph_pipeline(job_id: str, skill_name: str, prompt_text: str, slack_thread_ts: str, channel: str):
    """
    Redis(Celery)에서 꺼내어진 워커 태스크 엔트리 포인트입니다.
    이곳에서 Skill 로드 및 LangGraph 구동이 시작됩니다.
    """
    print(f"[{job_id}] Worker started for skill: {skill_name}")

    # 1. Skill Context 로드
    loader = SkillLoader(base_dir="c:\\Users\\user\\.gemini\\antigravity\\skills")
    try:
        skill_prompt = loader.load_skill_prompt(skill_name)
    except Exception as e:
        print(f"Skill Loading Error: {e}")
        skill_prompt = "Default Context"

    # 2. 다중 CLI Adapter Factory 분기 (슬랙 선택값 연동 모사)
    selected_cli = os.environ.get("SELECTED_CLI", "claude")
    
    if selected_cli == "cursor":
        from ..adapters.cursor import CursorCLIAdapter
        adapter = CursorCLIAdapter()
    elif selected_cli == "gemini":
        from ..adapters.gemini import GeminiCLIAdapter
        adapter = GeminiCLIAdapter()
    elif selected_cli == "codex":
        from ..adapters.codex import CodexCLIAdapter
        adapter = CodexCLIAdapter()
    else:
        from ..adapters.claude import ClaudeCLIAdapter
        adapter = ClaudeCLIAdapter()

    spec = JobSpec(
        job_id=job_id,
        skill_name=skill_name,
        prompt=f"{skill_prompt}\n\nTask:\n{prompt_text}",
        workspace_path="/app/workspace" # Sandbox 마운트 위치 가정
    )
    
    # 3. 서브프로세스 기동
    pid = await adapter.submit(spec)
    print(f"[{job_id}] Adapter spawned PID: {pid}")
    
    # 4. stdout 스트리밍 추출
    async for line in adapter.stream(job_id):
        # 본래는 여기에 SlackThrottler가 연동되어 슬랙에 메시지를 쏴줍니다.
        # await throttler.ingest_log(line)
        pass
