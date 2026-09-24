"""Simple thread-safe pacing limiter (official limit 1,200 req/min = 20 rps; we stay below)."""
import threading
import time


class RateLimiter:
    def __init__(self, rps):
        self.dt = 1.0 / rps
        self._next = time.monotonic()
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            t = max(now, self._next)
            self._next = t + self.dt
        time.sleep(max(0.0, t - now))
