import sys
import os
import asyncio

# Windows 터미널 인코딩을 UTF-8로 설정 (한국어, 특수문자 출력 깨짐 방지)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

# 프로젝트 루트의 .env 파일을 자동 로드 (bat 파일 없이 직접 실행해도 동작)
load_dotenv()

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
