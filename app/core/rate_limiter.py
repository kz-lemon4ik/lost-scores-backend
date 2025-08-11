import asyncio
from collections import deque
from time import monotonic


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float) -> None:
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = monotonic()
                while self._timestamps and now - self._timestamps[0] >= self.period_seconds:
                    self._timestamps.popleft()

                if len(self._timestamps) < self.max_calls:
                    self._timestamps.append(now)
                    return

                wait_for = self.period_seconds - (now - self._timestamps[0])

            # sleep outside the lock
            await asyncio.sleep(wait_for)


osu_api_rate_limiter = RateLimiter(max_calls=60, period_seconds=60.0)
