"""Small in-memory sliding-window limiter for authentication endpoints.

Per process only; a multi-worker deployment should move this to Redis.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, *, max_attempts: int, window_seconds: float) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts[key]
        while attempts and now - attempts[0] > self.window_seconds:
            attempts.popleft()
        return attempts

    def is_limited(self, key: str) -> bool:
        return len(self._prune(key, time.monotonic())) >= self.max_attempts

    def record(self, key: str) -> None:
        now = time.monotonic()
        self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)


login_failures = SlidingWindowLimiter(max_attempts=5, window_seconds=300)
