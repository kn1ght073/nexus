"""In-memory rate limiting and account lockout (security hardening).

The hosted control plane is a single uvicorn worker, so an in-memory
sliding-window store is both correct and dependency-free. When the control
plane is scaled to multiple workers, move these stores to Postgres/Redis
(noted in docs/deploy/online-access.md §"Scaling the control plane").

Two protections live here:
- `RateLimiter`: sliding-window request counters (per key) used to throttle
  login/register/relay attempts — brute-force resistance.
- `Lockout`: failed-attempt counters per account (email) that lock the
  account for a cool-off period after `max_failed` wrong passwords.
"""
import threading
import time


class RateLimiter:
    """Sliding-window counter: at most `limit` events per `window` seconds per key."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._events: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        events = self._events.get(key)
        if events:
            self._events[key] = [t for t in events if now - t < self.window]

    def allow(self, key: str) -> bool:
        """Record an event; True if it is within the limit, False if throttled."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            events = self._events.setdefault(key, [])
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True

    def retry_after(self, key: str) -> int:
        """Seconds until the oldest event leaves the window (for Retry-After)."""
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            events = self._events.get(key) or []
            if not events:
                return 0
            return max(0, int(self.window - (now - events[0])) + 1)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)


class Lockout:
    """Failed-attempt tracker per account: lock after `max_failed`, cool off `lockout_seconds`.

    Only *wrong-password* attempts count (a successful login clears the
    counter), and the locked state is bounded — a hard lockout counter that
    never resets would let an attacker permanently deny an account.
    """

    def __init__(self, max_failed: int, lockout_seconds: float) -> None:
        self.max_failed = max_failed
        self.lockout_seconds = lockout_seconds
        self._failed: dict[str, list[float]] = {}
        self._locked_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def is_locked(self, key: str) -> bool:
        with self._lock:
            locked = self._locked_at.get(key)
            if locked is None:
                return False
            if time.monotonic() - locked >= self.lockout_seconds:
                # cool-off elapsed: unlock and forget the failures
                self._locked_at.pop(key, None)
                self._failed.pop(key, None)
                return False
            return True

    def locked_for(self, key: str) -> int:
        """Seconds remaining in the lockout (0 when not locked)."""
        with self._lock:
            locked = self._locked_at.get(key)
            if locked is None:
                return 0
            return max(0, int(self.lockout_seconds - (time.monotonic() - locked)) + 1)

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._failed.setdefault(key, [])
            self._failed[key] = [t for t in self._failed[key] if now - t < self.lockout_seconds]
            self._failed[key].append(now)
            if len(self._failed[key]) >= self.max_failed:
                self._locked_at[key] = now

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failed.pop(key, None)
            self._locked_at.pop(key, None)
