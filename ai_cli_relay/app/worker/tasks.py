import os
import re
import asyncio
from pathlib import Path
from slack_sdk.web.async_client import AsyncWebClient
from .skill_loader import SkillLoader
from ..adapters.base import JobSpec
from ..bot.slack_throttler import SlackThrottler

# CLI 출력에 포함된 ANSI 색상/제어 코드 제거 (Slack 전송 전 정리)
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def _get_adapter(selected_cli: str):
    if selected_cli == "cursor":
        from ..adapters.cursor import CursorCLIAdapter
        return CursorCLIAdapter()
    elif selected_cli == "gemini":
        from ..adapters.gemini import GeminiCLIAdapter
        return GeminiCLIAdapter()
    elif selected_cli == "codex":
        from ..adapters.codex import CodexCLIAdapter
        return CodexCLIAdapter()
    else:
        from ..adapters.claude import ClaudeCLIAdapter
        return ClaudeCLIAdapter()


async def run_langgraph_pipeline(
    job_id: str,
    skill_name: str,
    prompt_text: str,
    slack_thread_ts: str,
    channel: str,
    slack_client: AsyncWebClient,
    timeout: int = None
):
    """
    AI CLI를 실행하고 stdout을 실시간으로 Slack 스레드에 스트리밍합니다.

    환경변수:
        SKILL_BASE_PATH  - 스킬 디렉토리 경로 (기본: ~/.gemini/antigravity/skills)
        WORKSPACE_PATH   - CLI 실행 작업 디렉토리 (기본: ~/workspace)
        SELECTED_CLI     - 사용할 CLI 종류: claude|cursor|gemini|codex (기본: claude)
        JOB_TIMEOUT      - 작업 타임아웃(초) (기본: 300)
    """
    timeout = timeout or int(os.environ.get("JOB_TIMEOUT", "300"))
    base_dir = os.environ.get(
        "SKILL_BASE_PATH",
        str(Path.home() / ".gemini" / "antigravity" / "skills")
    )
    workspace = os.environ.get("WORKSPACE_PATH", str(Path.home() / "workspace"))

    print(f"[{job_id}] Worker started | skill={skill_name} | cli={os.environ.get('SELECTED_CLI', 'claude')}")

    # 1. Skill Context 로드
    loader = SkillLoader(base_dir=base_dir)
    try:
        skill_prompt = loader.load_skill_prompt(skill_name)
    except Exception as e:
        print(f"[{job_id}] Skill loading error: {e}")
        skill_prompt = "Default Context"

    # 2. CLI Adapter 선택
    selected_cli = os.environ.get("SELECTED_CLI", "claude")
    adapter = _get_adapter(selected_cli)

    spec = JobSpec(
        job_id=job_id,
        skill_name=skill_name,
        prompt=f"{skill_prompt}\n\nTask:\n{prompt_text}",
        workspace_path=workspace
    )

    # 3. SlackThrottler 초기화 (chat.update + chat.postMessage 래핑)
    async def _update(ts: str, text: str) -> None:
        await slack_client.chat_update(channel=channel, ts=ts, text=text)

    async def _post_and_get_ts(text: str) -> str:
        resp = await slack_client.chat_postMessage(
            channel=channel,
            thread_ts=slack_thread_ts,
            text=text
        )
        return resp["ts"]

    throttler = SlackThrottler(
        update_func=_update,
        post_func=_post_and_get_ts,
        initial_ts=slack_thread_ts
    )

    try:
        # 4. 서브프로세스 기동
        pid = await adapter.submit(spec)
        print(f"[{job_id}] Spawned PID: {pid}")

        # 5. stdout 스트리밍 → SlackThrottler → Slack
        async def _stream_and_ingest():
            async for line in adapter.stream(job_id):
                clean = ANSI_ESCAPE.sub('', line)
                if clean.strip():
                    await throttler.ingest_log(clean)

        await asyncio.wait_for(_stream_and_ingest(), timeout=timeout)

    except asyncio.TimeoutError:
        await adapter.cancel(job_id)
        await throttler.ingest_log(f"\n⚠️ 작업 시간 초과 ({timeout}초). 프로세스가 중단되었습니다.")
        print(f"[{job_id}] Timeout after {timeout}s")

    except Exception as e:
        await throttler.ingest_log(f"\n❌ 오류 발생: {e}")
        print(f"[{job_id}] Error: {e}")

    finally:
        await throttler.close()
        print(f"[{job_id}] Pipeline finished")
