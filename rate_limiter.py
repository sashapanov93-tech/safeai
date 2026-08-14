"""Small in-memory sliding-window limiter for incoming Telegram updates."""

from collections import defaultdict, deque
from time import monotonic


class PerUserRateLimiter:
    """Allow at most ``limit`` events per user during a rolling time window."""

    def __init__(self, limit: int = 40, window_seconds: float = 60.0):
        if limit < 1 or window_seconds <= 0:
            raise ValueError("limit and window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._last_notice: dict[int, float] = {}
        self._checks = 0

    def allow(self, user_id: int, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        self._checks += 1
        if self._checks % 256 == 0:
            self._remove_expired_users(now)
        events = self._events[user_id]
        cutoff = now - self.window_seconds

        while events and events[0] <= cutoff:
            events.popleft()

        if len(events) >= self.limit:
            return False

        events.append(now)
        return True

    def should_notify(self, user_id: int, now: float | None = None) -> bool:
        """Permit one overload warning per user and time window."""
        now = monotonic() if now is None else now
        if now - self._last_notice.get(user_id, float("-inf")) < self.window_seconds:
            return False
        self._last_notice[user_id] = now
        return True

    def _remove_expired_users(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for user_id, events in list(self._events.items()):
            if not events or events[-1] <= cutoff:
                self._events.pop(user_id, None)
                self._last_notice.pop(user_id, None)
