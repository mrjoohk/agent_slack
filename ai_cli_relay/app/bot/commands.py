import re
import uuid
import asyncio
import os
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from ..worker.tasks import run_langgraph_pipeline

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
    if task.cancelled():
        print(f"[TASK] cancelled: {task.get_name()}", flush=True)
    elif task.exception():
        import traceback
        print(f"[TASK ERROR] {task.get_name()}", flush=True)
        traceback.print_exception(type(task.exception()), task.exception(),
                                  task.exception().__traceback__)


def register_listeners(app: AsyncApp):
    print("[BOOT] register_listeners called", flush=True)

    # NOTE: @app.event("message") 는 등록하지 않음.
    # Bolt는 첫 번째 매칭 리스너만 실행하므로, 여기 등록하면
    # @app.message(SKILL_PATTERN) 이 절대 실행되지 않음.

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
                    f"> {prompt_text}"
                )
            )

        for cli_name in cli_targets:
            job_id = str(uuid.uuid4())
            print(f"[7] posting ack for job={job_id[:8]} cli={cli_name}", flush=True)
            try:
                # 수신 확인 + 사용자 요청 프롬프트 전체 표시
                ack = await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=(
                        f"⏳ *[{skill_name} | {cli_name.upper()}]* 작업 시작 "
                        f"(Job: `{job_id[:8]}`)\n"
                        f"```\n{prompt_text}\n```"
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

    # 봇 자신이 보낸 메시지 이벤트 (chat_postMessage → bot_message 이벤트로 수신)
    # 처리하지 않으면 "Unhandled request" 경고가 반복 출력됨
    @app.event({"type": "message", "subtype": "bot_message"})
    async def handle_bot_message():
        pass  # 무시

    # chat_update 호출 시 발생하는 message_changed 이벤트
    @app.event({"type": "message", "subtype": "message_changed"})
    async def handle_message_changed():
        pass  # 무시

    # message_deleted 이벤트도 동일하게 무시
    @app.event({"type": "message", "subtype": "message_deleted"})
    async def handle_message_deleted():
        pass  # 무시

    # SKILL_PATTERN에 매칭되지 않는 일반 메시지 → 사용법 안내
    # 반드시 @app.message(SKILL_PATTERN) 뒤에 등록해야 함
    @app.event("message")
    async def handle_unmatched_message(event, client: AsyncWebClient):
        # 혹시 남은 subtype 이벤트나 bot 메시지는 무시
        if event.get("subtype") or event.get("bot_id"):
            return
        channel = event.get("channel")
        thread_ts = event.get("ts")
        await client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=(
                "❓ 명령어 형식이 올바르지 않습니다.\n\n"
                "*사용법:*\n"
                "```\n"
                "skill[스킬명:CLI명] 요청 내용\n"
                "```\n"
                "*예시:*\n"
                "• `skill[core:claude] 피보나치 수열 구현해줘`\n"
                "• `skill[core:gemini] 이 코드 리뷰해줘`\n"
                "• `skill[core:claude,gemini] 두 관점에서 비교해줘`\n"
                "• `skill[core:all] 전부 실행해봐`"
            ),
        )
