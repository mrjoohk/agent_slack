import re
import uuid
import asyncio
import os
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from ..worker.tasks import run_langgraph_pipeline

# 새 문법: agent[cli_spec] skill[name](선택) 요청
# 예시:
#   agent[claude] skill[core] 피보나치 구현해줘
#   agent[claude,gemini] skill[core] 비교해줘
#   agent[all] skill[core] 전부 실행해봐
#   agent[claude] 스킬 없이 바로 실행
#   @봇멘션 agent[claude] skill[core] 요청
AGENT_SKILL_PATTERN = re.compile(
    r"^(?:<@[A-Z0-9]+>\s*)?"           # 선택적 @멘션
    r"agent\s*\[([^\]]+)\]"            # agent[cli_spec] — 필수
    r"(?:\s+skill\s*\[([^\]]+)\])?"    # skill[name]     — 선택
    r"\s*(.*)?$",                       # 요청 프롬프트
    re.IGNORECASE | re.DOTALL,
)

# 스킬명 허용 문자 (경로 순회 방지)
VALID_SKILL_NAME = re.compile(r'^[a-zA-Z0-9_-]+$')

# 지원 CLI 목록
VALID_CLI_NAMES = {"claude", "gemini", "codex", "cursor"}


def _parse_cli_targets(cli_raw: str) -> list[str]:
    """
    'claude'        → ['claude']
    'claude,gemini' → ['claude', 'gemini']
    'all'           → sorted(VALID_CLI_NAMES)
    """
    cli_raw = cli_raw.strip().lower()
    if cli_raw == 'all':
        return sorted(VALID_CLI_NAMES)
    return [c.strip() for c in cli_raw.split(',') if c.strip()]


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

    @app.message(AGENT_SKILL_PATTERN)
    async def handle_agent_request(message, say, context, client: AsyncWebClient):
        print("[1] handle_agent_request entered", flush=True)

        matches = context.get("matches")
        print(f"[2] matches={matches}", flush=True)
        if not matches or len(matches) < 3:
            print("[2] matches missing — return", flush=True)
            return

        cli_raw     = (matches[0] or "").strip()
        skill_name  = (matches[1] or "").strip() or None   # None이면 스킬 없이 실행
        prompt_text = (matches[2] or "").strip()
        thread_ts   = message.get("ts")
        channel     = message.get("channel")

        print(f"[3] cli_raw={cli_raw!r} skill={skill_name!r} "
              f"prompt={prompt_text[:40]!r}", flush=True)

        # 프롬프트 필수
        if not prompt_text:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 요청 내용을 입력해주세요.\n예: `agent[claude] skill[core] 작업 내용`"
            )
            return

        # 스킬명 검증 (지정된 경우만)
        if skill_name and not VALID_SKILL_NAME.match(skill_name):
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 유효하지 않은 스킬명입니다. 영문자, 숫자, `-`, `_`만 허용됩니다."
            )
            return

        # CLI 파싱 및 검증
        cli_targets = _parse_cli_targets(cli_raw)
        if not cli_targets:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ CLI를 지정해주세요.\n예: `agent[claude]` 또는 `agent[claude,gemini]`"
            )
            return

        invalid = [c for c in cli_targets if c not in VALID_CLI_NAMES]
        if invalid:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text=(
                    f"❌ 알 수 없는 CLI: `{'`, `'.join(invalid)}`\n"
                    f"사용 가능: `{'`, `'.join(sorted(VALID_CLI_NAMES))}`"
                )
            )
            return

        print(f"[4] cli_targets={cli_targets} skill={skill_name!r}", flush=True)

        # 복수 CLI 분배 요약 메시지
        if len(cli_targets) > 1:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text=(
                    f"🚀 `{', '.join(cli_targets)}` "
                    f"{len(cli_targets)}개 CLI에 요청을 분배합니다.\n"
                    f"> {prompt_text}"
                )
            )

        for cli_name in cli_targets:
            job_id = str(uuid.uuid4())
            skill_label = f" | skill:{skill_name}" if skill_name else ""
            print(f"[5] posting ack job={job_id[:8]} cli={cli_name} skill={skill_name!r}",
                  flush=True)
            try:
                ack = await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=(
                        f"⏳ *[{cli_name.upper()}{skill_label}]* 작업 시작 "
                        f"(Job: `{job_id[:8]}`)\n"
                        f"```\n{prompt_text}\n```"
                    )
                )
                print(f"[6] ack posted ts={ack['ts']}", flush=True)
            except Exception as e:
                print(f"[6] ack postMessage FAILED: {e}", flush=True)
                continue

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
            print(f"[7] task created: {task.get_name()}", flush=True)

    # 봇 자신이 보낸 메시지 이벤트 — 무시
    @app.event({"type": "message", "subtype": "bot_message"})
    async def handle_bot_message():
        pass

    # chat_update 시 발생하는 message_changed 이벤트 — 무시
    @app.event({"type": "message", "subtype": "message_changed"})
    async def handle_message_changed():
        pass

    @app.event({"type": "message", "subtype": "message_deleted"})
    async def handle_message_deleted():
        pass

    # 패턴 미매칭 메시지 → 사용법 안내
    @app.event("message")
    async def handle_unmatched_message(event, client: AsyncWebClient):
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
                "agent[CLI명] skill[스킬명] 요청 내용\n"
                "```\n"
                "*예시:*\n"
                "• `agent[claude] skill[core] 피보나치 수열 구현해줘`\n"
                "• `agent[gemini] skill[core] 이 코드 리뷰해줘`\n"
                "• `agent[claude,gemini] skill[core] 두 관점에서 비교해줘`\n"
                "• `agent[all] skill[core] 전부 실행해봐`\n"
                "• `agent[claude] 스킬 없이 바로 질문`"
            ),
        )
