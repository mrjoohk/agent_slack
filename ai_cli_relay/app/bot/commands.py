import re
import uuid
import asyncio
import os
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from ..worker.tasks import run_langgraph_pipeline

# 메시지 파싱 패턴: skill[스킬명] 또는 skill[스킬명:CLI] 프롬프트
# 채널에서 봇 멘션(@bot) 후 명령어를 입력하면 텍스트 앞에 <@USER_ID> 가 붙으므로
# 선택적으로 허용 (DM이나 멘션 없는 채널 메시지도 모두 처리)
SKILL_PATTERN = re.compile(
    r"^(?:<@[A-Z0-9]+>\s*)?skill\s*\[(.*?)\]\s*(.*)$",
    re.IGNORECASE | re.DOTALL,
)

# 스킬명 허용 문자 (경로 순회 방지)
VALID_SKILL_NAME = re.compile(r'^[a-zA-Z0-9_-]+$')

# 지원 CLI 목록
VALID_CLI_NAMES = {"claude", "gemini", "codex", "cursor"}


def _parse_skill_spec(raw: str) -> tuple[str, list[str] | None]:
    if ':' in raw:
        skill_name, cli_raw = raw.split(':', 1)
        cli_raw = cli_raw.strip().lower()
        if cli_raw == 'all':
            cli_targets = sorted(VALID_CLI_NAMES)
        else:
            cli_targets = [c.strip() for c in cli_raw.split(',') if c.strip()]
    else:
        skill_name = raw
        cli_targets = None
    return skill_name.strip(), cli_targets


def _log_task_error(task: asyncio.Task) -> None:
    """asyncio.create_task() 예외를 콘솔에 출력 (기본적으로 무시되므로 명시적 핸들러 필요)"""
    if task.cancelled():
        print(f"[TASK] cancelled: {task.get_name()}", flush=True)
    elif task.exception():
        import traceback
        print(f"[TASK ERROR] {task.get_name()}", flush=True)
        traceback.print_exception(type(task.exception()), task.exception(),
                                  task.exception().__traceback__)


def register_listeners(app: AsyncApp):
    print("[BOOT] register_listeners called", flush=True)

    # 모든 message 이벤트를 잡아서 raw 구조 출력 (패턴 매칭 전 확인용)
    @app.event("message")
    async def debug_raw_message(event, body):
        import json
        print("[RAW EVENT] message received:", flush=True)
        print(json.dumps(event, ensure_ascii=False, indent=2), flush=True)

    @app.message(SKILL_PATTERN)
    async def handle_skill_request(message, say, context, client: AsyncWebClient):
        print("[1] handle_skill_request entered", flush=True)

        matches = context.get("matches")
        print(f"[2] matches={matches}", flush=True)
        if not matches or len(matches) < 2:
            print("[2] matches missing — return", flush=True)
            return

        raw_spec    = matches[0].strip()
        prompt_text = matches[1].strip()
        thread_ts   = message.get("ts")
        channel     = message.get("channel")
        print(f"[3] raw_spec={raw_spec!r} prompt={prompt_text[:40]!r} "
              f"channel={channel} ts={thread_ts}", flush=True)

        skill_name, cli_targets = _parse_skill_spec(raw_spec)
        print(f"[4] skill_name={skill_name!r} cli_targets={cli_targets}", flush=True)

        # 스킬명 검증
        if not VALID_SKILL_NAME.match(skill_name):
            print(f"[4] invalid skill name: {skill_name!r}", flush=True)
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 유효하지 않은 스킬명입니다. 영문자, 숫자, `-`, `_`만 허용됩니다."
            )
            return

        if not prompt_text:
            print("[4] empty prompt — return", flush=True)
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 프롬프트를 입력해주세요.\n예: `skill[core:claude] 작업 내용`"
            )
            return

        # CLI 기본값
        if cli_targets is None:
            default = os.environ.get("DEFAULT_CLI") or os.environ.get("SELECTED_CLI", "claude")
            cli_targets = [default.strip().lower()]
            print(f"[5] cli_targets defaulted to {cli_targets}", flush=True)

        # CLI 이름 검증
        invalid = [c for c in cli_targets if c not in VALID_CLI_NAMES]
        if invalid:
            print(f"[5] invalid CLI names: {invalid}", flush=True)
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text=(
                    f"❌ 알 수 없는 CLI: `{'`, `'.join(invalid)}`\n"
                    f"사용 가능: `{'`, `'.join(sorted(VALID_CLI_NAMES))}`"
                )
            )
            return

        print(f"[6] dispatching to cli_targets={cli_targets}", flush=True)

        # 복수 CLI면 분배 요약 메시지
        if len(cli_targets) > 1:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text=(
                    f"🚀 *[{skill_name}]* "
                    f"`{', '.join(cli_targets)}` "
                    f"{len(cli_targets)}개 CLI에 요청을 분배합니다.\n"
                    f"> {prompt_text[:80]}"
                )
            )

        for cli_name in cli_targets:
            job_id = str(uuid.uuid4())
            print(f"[7] posting ack for job={job_id[:8]} cli={cli_name}", flush=True)
            try:
                ack = await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=(
                        f"⏳ *[{skill_name} | {cli_name.upper()}]* "
                        f"작업 시작... (Job: `{job_id[:8]}`)\n"
                        f"> {prompt_text[:80]}"
                    )
                )
                print(f"[8] ack posted ts={ack['ts']}", flush=True)
            except Exception as e:
                print(f"[8] ack postMessage FAILED: {e}", flush=True)
                continue

            print(f"[9] creating asyncio task for job={job_id[:8]}", flush=True)
            task = asyncio.create_task(
                run_langgraph_pipeline(
                    job_id=job_id,
                    skill_name=skill_name,
                    prompt_text=prompt_text,
                    slack_thread_ts=ack["ts"],
                    channel=channel,
                    slack_client=client,
                    cli_name=cli_name,
                ),
                name=f"job-{job_id[:8]}-{cli_name}",
            )
            task.add_done_callback(_log_task_error)
            print(f"[9] task created: {task.get_name()}", flush=True)
