import re
from slack_bolt.async_app import AsyncApp
from slack_sdk.web.async_client import AsyncWebClient

# 이슈1 대화형 명령어 파싱: skill[스킬명] 프롬프트 텍스트
SKILL_PATTERN = re.compile(r"^skill\s*\[(.*?)\]\s*(.*)$", re.IGNORECASE | re.DOTALL)

def register_listeners(app: AsyncApp):
    @app.message(SKILL_PATTERN)
    async def handle_skill_request(message, say, context, client: AsyncWebClient):
        # 정규식 캡처 그룹
        matches = context.get("matches")
        if not matches or len(matches) < 2:
            return
            
        skill_name = matches[0].strip()
        prompt_text = matches[1].strip()
        
        thread_ts = message.get("ts")
        channel = message.get("channel")
        
        # 1. 스레드 초기화 메시지 발송
        ack_msg = await say(
            text=f"⏳ *[{skill_name}]* 스킬 기반 작업을 할당 중입니다...\n> {prompt_text[:50]}...",
            thread_ts=thread_ts
        )
        
        # 2. Redis/Celery Queue 전송 로직 (추후 연동)
        # job_id = dispatch_to_queue(skill_name, prompt_text, channel, ack_msg['ts'])
        dummy_job_id = "job-uuid-1234"
        
        await client.chat_update(
            channel=channel,
            ts=ack_msg["ts"],
            text=f"✅ *[{skill_name}]* 작업을 Worker에 인계했습니다. (Job ID: {dummy_job_id})"
        )
