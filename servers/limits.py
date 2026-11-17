"""Pure, clock-injectable abuse limits for the SSH gateway.

Kept free of I/O so every rule can be unit tested deterministically.
"""

import time
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import dataclass

Clock = Callable[[], float]


@dataclass(frozen=True)
class LimitConfig:
    """Tunables, all overridable from the environment (see :meth:`from_env`)."""

    max_sessions: int = 50
    max_sessions_per_ip: int = 5
    idle_timeout: float = 15 * 60
    max_session_seconds: float = 60 * 60
    rate_burst: int = 10
    rate_per_minute: float = 20

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "LimitConfig":
        """Read ``SSH_*`` variables, falling back to the defaults."""
        defaults = cls()

        def number(name: str, default: float) -> float:
            raw = environ.get(name)
            if raw is None or raw == "":
                return default
            value = float(raw)
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {raw!r}")
            return value

        return cls(
            max_sessions=int(number("SSH_MAX_SESSIONS", defaults.max_sessions)),
            max_sessions_per_ip=int(number("SSH_MAX_PER_IP", defaults.max_sessions_per_ip)),
            idle_timeout=number("SSH_IDLE_TIMEOUT", defaults.idle_timeout),
            max_session_seconds=number("SSH_MAX_SESSION_SECONDS", defaults.max_session_seconds),
            rate_burst=int(number("SSH_RATE_BURST", defaults.rate_burst)),
            rate_per_minute=number("SSH_RATE_PER_MINUTE", defaults.rate_per_minute),
        )


class TokenBucket:
    """Classic token bucket: ``capacity`` burst, refilled at ``rate`` tokens/second."""

    def __init__(self, capacity: int, rate: float, clock: Clock) -> None:
        self.capacity = capacity
        self.rate = rate
        self.clock = clock
        self.tokens = float(capacity)
        self.updated = clock()

    def take(self) -> bool:
        """Consume one token if available."""
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    @property
    def full(self) -> bool:
        """True when the bucket has fully refilled (safe to forget)."""
        elapsed = self.clock() - self.updated
        return self.tokens + elapsed * self.rate >= self.capacity


class SessionLimiter:
    """Connection rate limiting plus global and per-IP session caps."""

    def __init__(self, config: LimitConfig, clock: Clock = time.monotonic) -> None:
        self.config = config
        self.clock = clock
        self._buckets: dict[str, TokenBucket] = {}
        self._active: defaultdict[str, int] = defaultdict(int)

    @property
    def active_total(self) -> int:
        """Sessions currently holding a slot."""
        return sum(self._active.values())

    def active_for(self, ip: str) -> int:
        """Sessions currently held by ``ip``."""
        return self._active.get(ip, 0)

    def allow_connection(self, ip: str) -> bool:
        """Rate-limit new TCP connections per IP."""
        self._forget_idle_buckets()
        bucket = self._buckets.get(ip)
        if bucket is None:
            bucket = TokenBucket(
                self.config.rate_burst, self.config.rate_per_minute / 60, self.clock
            )
            self._buckets[ip] = bucket
        return bucket.take()

    def acquire(self, ip: str) -> str | None:
        """Reserve a session slot; returns ``None`` on success or a rejection reason."""
        if self.active_total >= self.config.max_sessions:
            return "server_full"
        if self.active_for(ip) >= self.config.max_sessions_per_ip:
            return "too_many_sessions_from_ip"
        self._active[ip] += 1
        return None

    def release(self, ip: str) -> None:
        """Free a slot previously granted by :meth:`acquire`."""
        if self._active.get(ip, 0) <= 1:
            self._active.pop(ip, None)
        else:
            self._active[ip] -= 1

    def _forget_idle_buckets(self) -> None:
        """Bound memory: drop buckets that have fully refilled."""
        if len(self._buckets) > 1024:
            for ip in [ip for ip, bucket in self._buckets.items() if bucket.full]:
                del self._buckets[ip]


def expiry_reason(
    now: float, started: float, last_activity: float, config: LimitConfig
) -> str | None:
    """Why a session should be closed right now, if at all."""
    if now - started >= config.max_session_seconds:
        return "max_session_length"
    if now - last_activity >= config.idle_timeout:
        return "idle_timeout"
    return None
