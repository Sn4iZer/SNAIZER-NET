"""SSH gateway hardening: open auth, PTY shell only, limits, no forwarding."""

import asyncio
import os
import stat
import sys

import asyncssh
import pytest

from servers.limits import LimitConfig
from servers.ssh_server import (
    Gateway,
    GatewayConfig,
    PortfolioServer,
    RejectedSession,
    child_environment,
    load_or_create_host_key,
    sanitize_term,
)

POSIX = os.name == "posix"


def test_sanitize_term():
    assert sanitize_term("xterm-256color") == "xterm-256color"
    assert sanitize_term("screen.xterm+new") == "screen.xterm+new"
    assert sanitize_term("xterm; rm -rf /") == "xterm-256color"
    assert sanitize_term("") == "xterm-256color"
    assert sanitize_term(None) == "xterm-256color"


def test_child_environment_is_minimal(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "hunter2")
    env = child_environment("xterm", 120, 40)
    assert env["SNAIZER_MODE"] == "ssh"
    assert (env["TERM"], env["COLUMNS"], env["LINES"]) == ("xterm", "120", "40")
    assert "AWS_SECRET_ACCESS_KEY" not in env


def test_host_key_is_persistent(tmp_path):
    path = tmp_path / "data" / "ssh_host_key"
    first = load_or_create_host_key(path)
    second = load_or_create_host_key(path)
    assert first.get_fingerprint() == second.get_fingerprint()
    if POSIX:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def make_server(**limits) -> PortfolioServer:
    gateway = Gateway(GatewayConfig(limits=LimitConfig(**limits)))
    server = PortfolioServer(gateway)
    server.ip = "203.0.113.7"
    return server


def test_server_policy_methods():
    server = make_server()
    assert server.begin_auth("anyone") is False  # no auth required
    assert server.connection_requested("10.0.0.1", 22, "", 0) is False
    assert server.server_requested("", 8080) is False
    assert server.unix_connection_requested("/var/run/docker.sock") is False
    assert server.unix_server_requested("/tmp/x") is False
    assert server.tun_requested(None) is False
    assert server.tap_requested(None) is False


def test_one_session_per_connection():
    server = make_server()
    assert server.session_requested() not in (False, None)
    assert server.session_requested() is False


def test_session_limit_returns_rejected_session():
    server = make_server(max_sessions_per_ip=1)
    server.gateway.limiter.acquire(server.ip)  # someone from the same IP is connected
    session = server.session_requested()
    assert isinstance(session, RejectedSession)
    assert session.reason == "too_many_sessions_from_ip"
    assert not server.has_slot


def test_slot_released_on_disconnect():
    server = make_server()
    server.session_requested()
    assert server.gateway.limiter.active_for(server.ip) == 1
    server.connection_lost(None)
    assert server.gateway.limiter.active_for(server.ip) == 0


# -- live gateway tests (asyncssh client <-> server over localhost) ------


@pytest.fixture
async def gateway(tmp_path):
    instances = []

    async def start(**limits):
        config = GatewayConfig(
            host="127.0.0.1",
            port=0,
            host_key_path=tmp_path / "ssh_host_key",
            limits=LimitConfig(**limits),
            app_argv=(
                sys.executable,
                "-c",
                "import os, sys; print('SIZE', *os.get_terminal_size()); sys.stdin.readline()",
            ),
        )
        gw = Gateway(config)
        acceptor = await gw.start()
        port = acceptor.sockets[0].getsockname()[1]
        instances.append(acceptor)
        return gw, port

    yield start
    for acceptor in instances:
        acceptor.close()
        await acceptor.wait_closed()


def connect(port: int):
    return asyncssh.connect(
        "127.0.0.1", port, username="guest", known_hosts=None, agent_path=None, client_keys=None
    )


async def test_exec_is_rejected(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        with pytest.raises((asyncssh.ChannelOpenError, asyncssh.ProcessError, OSError)):
            await conn.run("id", check=True)


async def test_sftp_subsystem_is_rejected(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        with pytest.raises((asyncssh.ChannelOpenError, asyncssh.SFTPError, OSError)):
            async with conn.start_sftp_client():
                pass


async def test_local_forwarding_is_rejected(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        with pytest.raises(asyncssh.ChannelOpenError):
            await conn.open_connection("127.0.0.1", port)


async def test_remote_forwarding_is_rejected(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        with pytest.raises(asyncssh.ChannelListenError):
            await conn.forward_remote_port("127.0.0.1", 0, "127.0.0.1", 9)


async def test_connection_rate_limit(gateway):
    _, port = await gateway(rate_burst=2, rate_per_minute=1)
    async with connect(port), connect(port):
        with pytest.raises((asyncssh.DisconnectError, ConnectionError, OSError)):
            async with connect(port):
                pass


async def read_until(process, needle: str, timeout: float = 10.0) -> str:
    seen = ""
    async with asyncio.timeout(timeout):
        while needle not in seen:
            chunk = await process.stdout.read(4096)
            if not chunk:
                break
            seen += chunk
    return seen


async def test_per_ip_session_limit_shows_message(gateway):
    _, port = await gateway(max_sessions_per_ip=1)
    async with connect(port) as first:
        holder = await first.create_process(term_type="xterm", term_size=(80, 24))
        async with connect(port) as second:
            rejected = await second.create_process(term_type="xterm", term_size=(80, 24))
            text = await read_until(rejected, "TOO MANY LINKS")
            assert "TOO MANY LINKS" in text
            await rejected.wait_closed()
        holder.close()


@pytest.mark.skipif(not POSIX, reason="PTY sessions need Linux/macOS")
async def test_pty_session_runs_app_with_client_size_and_exits(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        process = await conn.create_process(term_type="xterm-256color", term_size=(123, 45))
        assert "SIZE 123 45" in await read_until(process, "SIZE 123 45")
        process.stdin.write("\n")
        result = await asyncio.wait_for(process.wait(), 10)
        assert result.exit_status == 0


@pytest.mark.skipif(os.name == "posix", reason="Windows-only fallback message")
async def test_windows_explains_pty_requirement(gateway):
    _, port = await gateway()
    async with connect(port) as conn:
        process = await conn.create_process(term_type="xterm", term_size=(80, 24))
        assert "Linux or macOS" in await read_until(process, "Linux or macOS")
