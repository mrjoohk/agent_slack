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


def _get_adapter(cli_name: str):
    if cli_name == "cursor":
        from ..adapters.cursor import CursorCLIAdapter
        return CursorCLIAdapter()
    elif cli_name == "gemini":
        from ..adapters.gemini import GeminiCLIAdapter
        return GeminiCLIAdapter()
    elif cli_name == "codex":
        from ..adapters.codex import CodexCLIAdapter
        return CodexCLIAdapter()
    else:
        from ..adapters.claude import ClaudeCLIAdapter
        return ClaudeCLIAdapter()


async def run_langgraph_pipeline(
    job_id: str,
    skill_name: str | None,   # None이면 스킬 없이 prompt_text만 실행
    prompt_text: str,
    slack_thread_ts: str,
    channel: str,
    slack_client: AsyncWebClient,
    cli_name: str = None,
    timeout: int = None,
):
    selected_cli = (
        cli_name
        or os.environ.get("DEFAULT_CLI")
        or os.environ.get("SELECTED_CLI", "claude")
    ).lower()

    timeout = timeout or int(os.environ.get("JOB_TIMEOUT", "300"))
    base_dir = os.environ.get(
        "SKILL_BASE_PATH",
        str(Path.home() / ".gemini" / "antigravity" / "skills")
    )
    workspace = os.environ.get("WORKSPACE_PATH", str(Path.home() / "workspace"))

    print(f"[{job_id[:8]}] PIPELINE START | skill={skill_name} cli={selected_cli} "
          f"timeout={timeout}", flush=True)
    print(f"[{job_id[:8]}] SKILL_BASE_PATH={base_dir}", flush=True)
    print(f"[{job_id[:8]}] WORKSPACE_PATH={workspace}", flush=True)

    # 1. Skill 로드 (skill_name이 None이면 스킬 없이 실행)
    if skill_name:
        print(f"[{job_id[:8]}] step1: loading skill={skill_name!r}...", flush=True)
        loader = SkillLoader(base_dir=base_dir)
        try:
            skill_prompt = loader.load_skill_prompt(skill_name)
            print(f"[{job_id[:8]}] step1: skill loaded ({len(skill_prompt)} chars)",
                  flush=True)
        except FileNotFoundError as e:
            print(f"[{job_id[:8]}] step1: skill not found: {e}", flush=True)
            expected_path = str(Path(base_dir) / skill_name / "SKILL.md")
            await slack_client.chat_postMessage(
                channel=channel,
                thread_ts=slack_thread_ts,
                text=(
                    f"⚠️ 스킬 `{skill_name}` 을 찾을 수 없습니다.\n"
                    f"아래 경로에 SKILL.md 파일을 만들어주세요:\n"
                    f"```{expected_path}```"
                ),
            )
            print(f"[{job_id[:8]}] PIPELINE END (skill not found)", flush=True)
            return
        except Exception as e:
            print(f"[{job_id[:8]}] step1: skill load error: {e}", flush=True)
            skill_prompt = ""
    else:
        print(f"[{job_id[:8]}] step1: no skill specified — running without system prompt",
              flush=True)
        skill_prompt = ""

    # 2. Adapter 선택
    print(f"[{job_id[:8]}] step2: getting adapter for {selected_cli!r}", flush=True)
    adapter = _get_adapter(selected_cli)
    print(f"[{job_id[:8]}] step2: adapter={adapter.__class__.__name__}", flush=True)

    full_prompt = f"{skill_prompt}\n\nTask:\n{prompt_text}" if skill_prompt else prompt_text
    spec = JobSpec(
        job_id=job_id,
        skill_name=skill_name or "",
        prompt=full_prompt,
        workspace_path=workspace,
    )

    # 3. SlackThrottler 초기화
    async def _update(ts: str, text: str) -> None:
        print(f"[{job_id[:8]}] throttler: update ts={ts[:10]}", flush=True)
        await slack_client.chat_update(channel=channel, ts=ts, text=text)

    async def _post_and_get_ts(text: str) -> str:
        print(f"[{job_id[:8]}] throttler: postMessage (overflow)", flush=True)
        resp = await slack_client.chat_postMessage(
            channel=channel,
            thread_ts=slack_thread_ts,
            text=text,
        )
        return resp["ts"]

    throttler = SlackThrottler(
        update_func=_update,
        post_func=_post_and_get_ts,
        initial_ts=slack_thread_ts,
    )

    try:
        # 4. 서브프로세스 기동
        print(f"[{job_id[:8]}] step4: submitting to adapter...", flush=True)
        pid = await adapter.submit(spec)
        print(f"[{job_id[:8]}] step4: spawned PID={pid}", flush=True)

        # 5. stdout 스트리밍
        line_count = 0
        async def _stream_and_ingest():
            nonlocal line_count
            print(f"[{job_id[:8]}] step5: stream started", flush=True)
            async for line in adapter.stream(job_id):
                clean = ANSI_ESCAPE.sub('', line)
                if clean.strip():
                    line_count += 1
                    if line_count <= 3:
                        print(f"[{job_id[:8]}] step5: line#{line_count}: {clean[:60]!r}",
                              flush=True)
                    await throttler.ingest_log(clean)
            print(f"[{job_id[:8]}] step5: stream ended (total {line_count} lines)", flush=True)

        await asyncio.wait_for(_stream_and_ingest(), timeout=timeout)

    except asyncio.TimeoutError:
        await adapter.cancel(job_id)
        await throttler.ingest_log(
            f"\n⚠️ [{selected_cli.upper()}] 작업 시간 초과 ({timeout}초). "
            f"프로세스가 중단되었습니다."
        )
        print(f"[{job_id[:8]}] TIMEOUT after {timeout}s", flush=True)

    except Exception as e:
        import traceback
        print(f"[{job_id[:8]}] EXCEPTION: {e}", flush=True)
        traceback.print_exc()
        await throttler.ingest_log(f"\n❌ [{selected_cli.upper()}] 오류 발생: {e}")

    finally:
        print(f"[{job_id[:8]}] step6: closing throttler...", flush=True)
        await throttler.close()
        print(f"[{job_id[:8]}] PIPELINE END | cli={selected_cli}", flush=True)
