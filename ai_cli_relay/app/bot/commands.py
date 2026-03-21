import re
import uuid
import asyncio
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient
from ..worker.tasks import run_langgraph_pipeline

# 메시지 파싱 패턴: skill[스킬명] 프롬프트 텍스트
SKILL_PATTERN = re.compile(r"^skill\s*\[(.*?)\]\s*(.*)$", re.IGNORECASE | re.DOTALL)

# 스킬명 허용 문자: 영문자, 숫자, 하이픈, 언더스코어만 허용 (경로 순회 방지)
VALID_SKILL_NAME = re.compile(r'^[a-zA-Z0-9_-]+$')

def register_listeners(app: AsyncApp):
    @app.message(SKILL_PATTERN)
    async def handle_skill_request(message, say, context, client: AsyncWebClient):
        matches = context.get("matches")
        if not matches or len(matches) < 2:
            return

        skill_name = matches[0].strip()
        prompt_text = matches[1].strip()

        thread_ts = message.get("ts")
        channel = message.get("channel")

        # 스킬명 입력 검증
        if not VALID_SKILL_NAME.match(skill_name):
            await say(
                text="❌ 유효하지 않은 스킬명입니다. 영문자, 숫자, `-`, `_`만 허용됩니다.",
                thread_ts=thread_ts
            )
            return

        if not prompt_text:
            await say(
                text="❌ 프롬프트를 입력해주세요. 예: `skill[skill-name] 작업 내용`",
                thread_ts=thread_ts
            )
            return

        job_id = str(uuid.uuid4())

        # 1. 작업 시작 알림 메시지
        ack_msg = await say(
            text=f"⏳ *[{skill_name}]* 작업을 시작합니다... (Job: `{job_id[:8]}`)\n> {prompt_text[:80]}",
            thread_ts=thread_ts
        )

        # 2. 비동기 백그라운드 태스크로 파이프라인 실행 (Celery 없이 asyncio 활용)
        asyncio.create_task(run_langgraph_pipeline(
            job_id=job_id,
            skill_name=skill_name,
            prompt_text=prompt_text,
            slack_thread_ts=ack_msg["ts"],
            channel=channel,
            slack_client=client
        ))
