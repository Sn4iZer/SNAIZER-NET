import pytest

from servers.limits import LimitConfig, SessionLimiter, TokenBucket, expiry_reason


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_token_bucket_burst_and_refill():
    clock = FakeClock()
    bucket = TokenBucket(capacity=3, rate=1.0, clock=clock)
    assert [bucket.take() for _ in range(4)] == [True, True, True, False]
    clock.now += 1.0
    assert bucket.take()
    assert not bucket.take()
    clock.now += 100
    assert bucket.full


def test_connection_rate_limit_is_per_ip():
    clock = FakeClock()
    limiter = SessionLimiter(LimitConfig(rate_burst=2, rate_per_minute=60), clock)
    assert limiter.allow_connection("1.1.1.1")
    assert limiter.allow_connection("1.1.1.1")
    assert not limiter.allow_connection("1.1.1.1")
    assert limiter.allow_connection("2.2.2.2")
    clock.now += 1.0  # 60/min == 1 token per second
    assert limiter.allow_connection("1.1.1.1")


def test_per_ip_session_cap():
    limiter = SessionLimiter(LimitConfig(max_sessions=10, max_sessions_per_ip=2), FakeClock())
    assert limiter.acquire("1.1.1.1") is None
    assert limiter.acquire("1.1.1.1") is None
    assert limiter.acquire("1.1.1.1") == "too_many_sessions_from_ip"
    assert limiter.acquire("2.2.2.2") is None
    limiter.release("1.1.1.1")
    assert limiter.acquire("1.1.1.1") is None


def test_global_session_cap():
    limiter = SessionLimiter(LimitConfig(max_sessions=3, max_sessions_per_ip=5), FakeClock())
    for ip in ("a", "b", "c"):
        assert limiter.acquire(ip) is None
    assert limiter.acquire("d") == "server_full"
    assert limiter.active_total == 3
    limiter.release("b")
    assert limiter.active_for("b") == 0
    assert limiter.acquire("d") is None


def test_release_never_goes_negative():
    limiter = SessionLimiter(LimitConfig(), FakeClock())
    limiter.release("ghost")
    assert limiter.active_total == 0


def test_expiry_reasons():
    config = LimitConfig(idle_timeout=60, max_session_seconds=300)
    assert expiry_reason(now=100, started=0, last_activity=90, config=config) is None
    assert expiry_reason(now=100, started=0, last_activity=40, config=config) == "idle_timeout"
    assert (
        expiry_reason(now=300, started=0, last_activity=299, config=config) == "max_session_length"
    )


def test_config_from_env():
    config = LimitConfig.from_env(
        {"SSH_MAX_SESSIONS": "7", "SSH_MAX_PER_IP": "2", "SSH_IDLE_TIMEOUT": "30"}
    )
    assert (config.max_sessions, config.max_sessions_per_ip, config.idle_timeout) == (7, 2, 30)
    assert config.max_session_seconds == LimitConfig().max_session_seconds


def test_config_rejects_nonsense():
    with pytest.raises(ValueError):
        LimitConfig.from_env({"SSH_MAX_SESSIONS": "0"})
