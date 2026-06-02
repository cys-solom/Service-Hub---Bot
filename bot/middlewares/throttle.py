"""Throttle middleware — rate-limiting per user (FSM states are exempt)"""
import time
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self.user_last_time: dict[int, float] = {}

    async def __call__(
        self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message, data: dict[str, Any],
    ) -> Any:
        # ── Skip throttle when user is in an FSM state (input required) ──
        fsm_state = data.get("state")
        if fsm_state:
            current = await fsm_state.get_state()
            if current:  # user is waiting to input something → never throttle
                return await handler(event, data)

        # ── Normal per-user rate limit ──
        user_id = event.from_user.id if event.from_user else 0
        now = time.time()
        last = self.user_last_time.get(user_id, 0)
        if now - last < self.rate_limit:
            return  # Rate limited — silently drop
        self.user_last_time[user_id] = now
        return await handler(event, data)
