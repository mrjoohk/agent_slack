import sys
import os
import asyncio

# Windows: asyncio subprocess 사용을 위해 ProactorEventLoop 명시 설정
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from .bot.commands import register_listeners


def create_slack_app() -> AsyncApp:
    """
    Socket Mode 용 AsyncApp 생성.
    HTTP 웹훅 방식과 달리 signing_secret 불필요 — 인증은 WebSocket 연결 시 처리.
    """
    app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))
    register_listeners(app)
    return app


async def main():
    app = create_slack_app()
    handler = AsyncSocketModeHandler(
        app=app,
        app_token=os.environ.get("SLACK_APP_TOKEN"),  # xapp-... (App-Level Token)
    )
    print("[AI CLI Bot] Socket Mode 시작 — 포트포워딩 불필요, Slack 서버로 아웃바운드 연결")
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
