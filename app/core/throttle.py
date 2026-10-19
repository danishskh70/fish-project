import threading
import time
from collections.abc import Callable

MAX_KEYS = 10_000


class LoginThrottle:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def retry_after(self, key: str) -> int:
        """Seconds left on the lock for this key. 0 means not locked."""
        with self._lock:
            until = self._locked_until.get(key)
            if until is None:
                return 0
            remaining = until - self._clock()
            if remaining <= 0:
                del self._locked_until[key]
                self._failures.pop(key, None)
                return 0
            return int(remaining) + 1

    def record_failure(
        self, key: str, max_failures: int, lock_seconds: int
    ) -> None:
        with self._lock:
            now = self._clock()
            recent = [
                t for t in self._failures.get(key, []) if now - t < lock_seconds
            ]
            recent.append(now)
            self._failures[key] = recent
            if len(recent) >= max_failures:
                self._locked_until[key] = now + lock_seconds
            if len(self._failures) > MAX_KEYS:
                self._prune(now, lock_seconds)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()

    def _prune(self, now: float, lock_seconds: int) -> None:
        for key in list(self._failures):
            stale = all(now - t >= lock_seconds for t in self._failures[key])
            if stale and key not in self._locked_until:
                del self._failures[key]


login_throttle = LoginThrottle()