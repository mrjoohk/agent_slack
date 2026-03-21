import time
import asyncio
from typing import Callable, Coroutine

class SlackThrottler:
    """
    UF-04-A, UF-04-B: Log Aggregator & Slack Message Updater
    제약사항 4번 (4000자 초과 무한 로깅 오류) 해결: 
    메시지가 길어지면 새로운 Reply 스레드를 달아서 Pagination 처리함.
    """
    def __init__(self, 
                 update_func: Callable[[str, str], Coroutine], 
                 post_func: Callable[[str], Coroutine],
                 initial_ts: str,
                 debounce_interval: float = 1.0):
        """
        update_func: async def func(ts: str, text: str) -> None (chat.update)
        post_func: async def func(text: str) -> str (chat.postMessage, return new ts)
        initial_ts: 처음에 할당받은 쓰레드의 첫 메시지 타임스탬프
        """
        self.update_func = update_func
        self.post_func = post_func
        self.current_ts = initial_ts
        self.debounce_interval = debounce_interval
        
        self.block_buffer = ""
        self.last_update_time = 0.0
        self.lock = asyncio.Lock()
        
        self.MAX_BLOCK_LEN = 3900

    async def ingest_log(self, chunk: str):
        async with self.lock:
            self.block_buffer += chunk
            current_time = time.time()
            if current_time - self.last_update_time >= self.debounce_interval:
                await self._flush_internal()

    async def _flush_internal(self):
        if not self.block_buffer:
            return
            
        if len(self.block_buffer) > self.MAX_BLOCK_LEN:
            # 한도를 초과하면 최대치만큼 자른 블록을 업데이트함
            first_part = self.block_buffer[:self.MAX_BLOCK_LEN]
            rest_part = self.block_buffer[self.MAX_BLOCK_LEN:]
            
            try:
                await self.update_func(self.current_ts, f"```\n{first_part}\n```")
            except Exception as e:
                print(f"[SlackThrottler Error updating]: {e}")
                
            # 남은 파트를 위한 새로운 쓰레드 메시지 생성 (페이지네이션)
            try:
                new_ts = await self.post_func(f"```\n{rest_part}\n```")
                self.current_ts = new_ts
                self.block_buffer = rest_part
                self.last_update_time = time.time()
            except Exception as e:
                print(f"[SlackThrottler Error posting]: {e}")
                
        else:
            try:
                await self.update_func(self.current_ts, f"```\n{self.block_buffer}\n```")
                self.last_update_time = time.time()
            except Exception as e:
                print(f"[SlackThrottler Error updating]: {e}")

    async def close(self):
        async with self.lock:
            await self._flush_internal()
