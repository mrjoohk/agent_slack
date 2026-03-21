import re
import uuid
import asyncio
import os
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from ..worker.tasks import run_langgraph_pipeline

# 메시지 파싱 패턴: skill[스킬명] 또는 skill[스킬명:CLI] 프롬프트
SKILL_PATTERN = re.compile(r"^skill\s*\[(.*?)\]\s*(.*)$", re.IGNORECASE | re.DOTALL)

# 스킬명 허용 문자 (경로 순회 방지)
VALID_SKILL_NAME = re.compile(r'^[a-zA-Z0-9_-]+$')

# 지원 CLI 목록
VALID_CLI_NAMES = {"claude", "gemini", "codex", "cursor"}


def _parse_skill_spec(raw: str) -> tuple[str, list[str] | None]:
    """
    괄호 안 내용을 파싱해 (skill_name, cli_targets) 를 반환합니다.

    'core'               → ('core', None)              # DEFAULT_CLI 사용
    'core:claude'        → ('core', ['claude'])
    'core:claude,gemini' → ('core', ['claude', 'gemini'])
    'core:all'           → ('core', ['claude', 'codex', 'cursor', 'gemini'])
    """
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


def register_listeners(app: AsyncApp):
    @app.message(SKILL_PATTERN)
    async def handle_skill_request(message, say, context, client: AsyncWebClient):
        matches = context.get("matches")
        if not matches or len(matches) < 2:
            return

        raw_spec   = matches[0].strip()
        prompt_text = matches[1].strip()
        thread_ts  = message.get("ts")
        channel    = message.get("channel")

        skill_name, cli_targets = _parse_skill_spec(raw_spec)

        # 스킬명 검증
        if not VALID_SKILL_NAME.match(skill_name):
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 유효하지 않은 스킬명입니다. 영문자, 숫자, `-`, `_`만 허용됩니다."
            )
            return

        if not prompt_text:
            await client.chat_postMessage(
                channel=channel, thread_ts=thread_ts,
                text="❌ 프롬프트를 입력해주세요.\n예: `skill[core:claude] 작업 내용`"
            )
            return

        # CLI 기본값: DEFAULT_CLI → SELECTED_CLI → claude 순서로 폴백
        if cli_targets is None:
            default = os.environ.get("DEFAULT_CLI") or os.environ.get("SELECTED_CLI", "claude")
            cli_targets = [default.strip().lower()]

        # CLI 이름 검증
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

        # 복수 CLI면 분배 요약 메시지 먼저 전송
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

        # CLI별 독립 태스크 생성 (각자 ack 메시지 → 결과 스트리밍)
        for cli_name in cli_targets:
            job_id = str(uuid.uuid4())
            ack = await client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=(
                    f"⏳ *[{skill_name} | {cli_name.upper()}]* "
                    f"작업 시작... (Job: `{job_id[:8]}`)\n"
                    f"> {prompt_text[:80]}"
                )
            )
            asyncio.create_task(run_langgraph_pipeline(
                job_id=job_id,
                skill_name=skill_name,
                prompt_text=prompt_text,
                slack_thread_ts=ack["ts"],
                channel=channel,
                slack_client=client,
                cli_name=cli_name,
            ))
