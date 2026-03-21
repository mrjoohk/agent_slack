import sys
import os
import asyncio

# Windows: asyncio subprocess 사용을 위해 ProactorEventLoop 명시 설정
# (Python 3.8+ 기본값이나, 명시적으로 선언해 subprocess 호환성 보장)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Request
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from .bot.commands import register_listeners

app = FastAPI(title="AI CLI Orchestrator")

# Slack Bolt App Init
slack_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN", "xoxb-dummy"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", "dummy")
)
app_handler = AsyncSlackRequestHandler(slack_app)

# 커스텀 리스너 (대화형 커맨드 패턴) 등록
register_listeners(slack_app)

@app.post("/slack/events")
async def slack_events(req: Request):
    """Slack Socket Mode 대신 HTTP Endpoint로 Event API 처리 시 진입점"""
    return await app_handler.handle(req)

@app.get("/health")
def healthcheck():
    return {"status": "ok"}
