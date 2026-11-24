"""Bounded, ordered per-controller delivery; a slow peer cannot hold an action."""
import asyncio
import json
import logging
import time
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error.spire_latency")


class Delivery:
    def __init__(self, ws, authorize, send_lock):
        self.ws = ws
        self.authorize = authorize
        self.send_lock = send_lock
        self.queue = asyncio.Queue(maxsize=32)
        self.task = None
        self.closed = False

    def put(self, payload, action_id=None):
        if self.closed:
            return False
        start = time.perf_counter()
        text = payload if isinstance(payload, str) else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"))
        if len(text.encode()) > 4 * 1024 * 1024:
            self.closed = True
            if self.task:
                self.task.cancel()
            self.task = asyncio.create_task(self.close_socket(1009))
            return False
        serialized = (time.perf_counter() - start) * 1000
        try:
            self.queue.put_nowait((text, action_id, time.perf_counter(), serialized))
        except asyncio.QueueFull:
            self.closed = True
            if self.task:
                self.task.cancel()
            self.task = asyncio.create_task(self.close_socket(1013))
            return False
        if self.task is None:
            self.task = asyncio.create_task(self.run())
        return True

    async def close_socket(self, code):
        logger.info('spire_close code=%s', code)
        try:
            await asyncio.wait_for(self.ws.close(code=code), 2)
        except (Exception, asyncio.CancelledError):
            pass

    async def run(self):
        try:
            while True:
                text, action_id, queued, serialized = await self.queue.get()
                self.authorize()
                start = time.perf_counter()
                async with self.send_lock:
                    await asyncio.wait_for(self.ws.send_text(text), 2)
                if action_id:
                    logger.info(
                        "spire_delivery action_id=%s serialize_ms=%.3f queue_ms=%.3f send_ms=%.3f bytes=%s",
                        action_id, serialized, (start-queued)*1000,
                        (time.perf_counter()-start)*1000, len(text.encode()))
        except asyncio.CancelledError:
            raise
        except HTTPException as error:
            self.closed = True
            await self.close_socket(1008 if error.status_code in (401, 403) else 4001 if error.status_code == 409 else 1011)
        except Exception:
            self.closed = True
            await self.close_socket(1011)
        finally:
            self.closed = True

    async def stop(self):
        self.closed = True
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
