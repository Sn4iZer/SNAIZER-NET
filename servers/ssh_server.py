"""SSH gateway: ``ssh -p 2222 guest@host`` opens SNAIZER//NET.

Every session gets a fresh, isolated ``python -m snaizer_net --mode ssh``
process on its own PTY. Nothing else is reachable: no shell, no exec, no
SFTP/SCP, no port/agent/X11 forwarding. Any username is accepted without a
password (the fake login lives inside the app).

Environment (all optional):
    SSH_HOST / SSH_PORT              bind address (0.0.0.0:2222)
    SSH_HOST_KEY                     host key path (./data/ssh_host_key)
    SSH_MAX_SESSIONS                 global concurrent sessions (50)
    SSH_MAX_PER_IP                   concurrent sessions per IP (5)
    SSH_IDLE_TIMEOUT                 seconds without input before kick (900)
    SSH_MAX_SESSION_SECONDS          hard session cap in seconds (3600)
    SSH_RATE_BURST / SSH_RATE_PER_MINUTE   new-connection rate limit per IP (10 / 20)
"""

import asyncio
import contextlib
import json
import logging
import os
import re
import signal
import sys
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import asyncssh

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from servers.limits import LimitConfig, SessionLimiter, expiry_reason  # noqa: E402

if TYPE_CHECKING:
    from servers.pty_bridge import PtyProcess

log = logging.getLogger("snaizer.ssh")

RESET_TERMINAL = (
    b"\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l"  # mouse tracking off
    b"\x1b[?2004l\x1b[?1049l\x1b[?25h\x1b[0m"  # bracketed paste off, main screen, cursor
)
MESSAGES = {
    "no_pty": "SNAIZER//NET needs an interactive terminal. Try: ssh -t -p 2222 guest@host",
    "unsupported": "This gateway needs Linux or macOS to allocate PTYs (use Docker or WSL).",
    "spawn_failed": "The node failed to boot your session. Try again in a moment.",
    "server_full": "NODE AT CAPACITY: every slot is taken. Try again in a few minutes.",
    "too_many_sessions_from_ip": "TOO MANY LINKS from your address. Close one and retry.",
    "idle_timeout": "Link dropped: idle for too long. Stay frosty, runner.",
    "max_session_length": "Link dropped: maximum session length reached. Come back anytime.",
}
_SAFE_TERM = re.compile(r"^[A-Za-z0-9._+-]{1,32}$")


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log shippers and ``docker logs``."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize the record and its structured ``fields``."""
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    """Send structured JSON logs to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log.handlers[:] = [handler]
    log.setLevel(logging.INFO)
    log.propagate = False
    logging.getLogger("asyncssh").setLevel(logging.WARNING)


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Log a structured event (never include usernames, keystrokes or commands)."""
    log.log(level, event, extra={"fields": fields})


def sanitize_term(term: str | None) -> str:
    """Only pass through plausible TERM values."""
    return term if term and _SAFE_TERM.match(term) else "xterm-256color"


def child_environment(term: str, columns: int, rows: int) -> dict[str, str]:
    """Minimal environment for the app process; nothing from the client leaks in."""
    env = {
        "TERM": term,
        "COLUMNS": str(columns),
        "LINES": str(rows),
        "SNAIZER_MODE": "ssh",
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(ROOT),
    }
    for name in ("SNAIZER_CONTENT_DIR", "SNAIZER_NO_ANIM", "SNAIZER_COLORS"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    return env


@dataclass(frozen=True)
class GatewayConfig:
    """Where to listen and how to run sessions."""

    host: str = "0.0.0.0"
    port: int = 2222
    host_key_path: Path = ROOT / "data" / "ssh_host_key"
    limits: LimitConfig = field(default_factory=LimitConfig)
    app_argv: tuple[str, ...] = (sys.executable, "-m", "snaizer_net", "--mode", "ssh")
    watchdog_interval: float = 15.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "GatewayConfig":
        """Build from ``SSH_*`` environment variables."""
        defaults = cls()
        key_path = environ.get("SSH_HOST_KEY")
        return cls(
            host=environ.get("SSH_HOST", defaults.host),
            port=int(environ.get("SSH_PORT", defaults.port)),
            host_key_path=Path(key_path) if key_path else defaults.host_key_path,
            limits=LimitConfig.from_env(environ),
        )


def load_or_create_host_key(path: Path) -> asyncssh.SSHKey:
    """Load the persistent host key, generating it (mode 0600) on first run."""
    if path.exists():
        return asyncssh.read_private_key(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = asyncssh.generate_private_key("ssh-ed25519")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(key.export_private_key())
    log_event("host_key_generated", path=str(path))
    return key


class Gateway:
    """Shared state across connections: config, limiter and live sessions."""

    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.limiter = SessionLimiter(config.limits)
        self.sessions: set[PortfolioSession] = set()

    def server_factory(self) -> "PortfolioServer":
        """Called by asyncssh once per TCP connection."""
        return PortfolioServer(self)

    async def start(self) -> asyncssh.SSHAcceptor:
        """Start listening."""
        key = load_or_create_host_key(self.config.host_key_path)
        acceptor = await asyncssh.create_server(
            self.server_factory,
            self.config.host,
            self.config.port,
            server_host_keys=[key],
            server_version="SNAIZER-NET",
            encoding=None,
            line_editor=False,
            allow_pty=True,
            agent_forwarding=False,
            x11_forwarding=False,
            allow_scp=False,
            sftp_factory=None,
            password_auth=False,
            kbdint_auth=False,
            public_key_auth=False,
            login_timeout=30,
            keepalive_interval=30,
            keepalive_count_max=3,
        )
        log_event(
            "server_start",
            host=self.config.host,
            port=self.config.port,
            fingerprint=key.get_fingerprint(),
            limits=vars(self.config.limits),
        )
        return acceptor

    async def shutdown(self) -> None:
        """Terminate every running session process."""
        await asyncio.gather(*(session.stop("server_shutdown") for session in list(self.sessions)))


class PortfolioServer(asyncssh.SSHServer):
    """Per-connection policy: open auth, one session, no forwarding of any kind."""

    def __init__(self, gateway: Gateway) -> None:
        self.gateway = gateway
        self.conn_id = uuid.uuid4().hex[:8]
        self.ip = "unknown"
        self.opened = time.monotonic()
        self.has_slot = False
        self.session_requested_once = False

    def connection_made(self, conn: asyncssh.SSHServerConnection) -> None:
        """Rate-limit new connections per IP."""
        peer = conn.get_extra_info("peername")
        self.ip = str(peer[0]) if peer else "unknown"
        if not self.gateway.limiter.allow_connection(self.ip):
            log_event("connection_rejected", ip=self.ip, conn=self.conn_id, reason="rate_limited")
            conn.disconnect(asyncssh.DISC_TOO_MANY_CONNECTIONS, "rate limited, slow down runner")
            return
        log_event("connection_open", ip=self.ip, conn=self.conn_id)

    def connection_lost(self, exc: Exception | None) -> None:
        """Free the session slot."""
        if self.has_slot:
            self.has_slot = False
            self.gateway.limiter.release(self.ip)
        log_event(
            "connection_closed",
            ip=self.ip,
            conn=self.conn_id,
            duration=round(time.monotonic() - self.opened, 1),
        )

    def begin_auth(self, username: str) -> bool:
        """No authentication required (public portfolio, fake login is in-app)."""
        return False

    def session_requested(self) -> "asyncssh.SSHServerSession[bytes] | bool":
        """Allow exactly one session per connection, within global/per-IP caps."""
        if self.session_requested_once:
            self._reject("extra_session")
            return False
        self.session_requested_once = True
        reason = self.gateway.limiter.acquire(self.ip)
        if reason is not None:
            log_event("session_rejected", ip=self.ip, conn=self.conn_id, reason=reason)
            return RejectedSession(reason)
        self.has_slot = True
        return PortfolioSession(self)

    def connection_requested(
        self, dest_host: str, dest_port: int, orig_host: str, orig_port: int
    ) -> bool:
        """Reject local port forwarding (direct-tcpip)."""
        return self._reject("direct_tcpip")

    def server_requested(self, listen_host: str, listen_port: int) -> bool:
        """Reject remote port forwarding (tcpip-forward)."""
        return self._reject("tcpip_forward")

    def unix_connection_requested(self, dest_path: str) -> bool:
        """Reject UNIX socket forwarding."""
        return self._reject("direct_streamlocal")

    def unix_server_requested(self, listen_path: str) -> bool:
        """Reject remote UNIX socket forwarding."""
        return self._reject("streamlocal_forward")

    def tun_requested(self, unit: int | None) -> bool:
        """Reject layer-3 tunnels."""
        return self._reject("tun")

    def tap_requested(self, unit: int | None) -> bool:
        """Reject layer-2 tunnels."""
        return self._reject("tap")

    def _reject(self, kind: str) -> bool:
        log_event("request_rejected", ip=self.ip, conn=self.conn_id, kind=kind)
        return False


class _BaseSession(asyncssh.SSHServerSession):  # type: ignore[type-arg]
    """Shared request policy: PTY + interactive shell only."""

    def __init__(self, server: PortfolioServer) -> None:
        self.server = server
        self.chan: asyncssh.SSHServerChannel[bytes] | None = None

    def connection_made(self, chan: "asyncssh.SSHServerChannel[bytes]") -> None:
        """Keep the channel."""
        self.chan = chan

    def shell_requested(self) -> bool:
        """The "shell" is the portfolio app, nothing else."""
        return True

    def exec_requested(self, command: str) -> bool:
        """``ssh host <command>`` is refused (the command is not logged)."""
        return self.server._reject("exec")

    def subsystem_requested(self, subsystem: str) -> bool:
        """SFTP and every other subsystem are refused."""
        return self.server._reject("subsystem")

    def break_received(self, msec: int) -> bool:
        """Ignore BREAK."""
        return False

    def send(self, data: bytes) -> None:
        """Write to the client, ignoring an already-closed channel."""
        if self.chan is not None:
            with contextlib.suppress(OSError, asyncssh.Error):
                self.chan.write(data)

    def finish(self, message_key: str | None, code: int) -> None:
        """Print an optional message and close the channel with an exit status."""
        if message_key in MESSAGES:
            self.send(f"\r\n\x1b[1;35m{MESSAGES[message_key]}\x1b[0m\r\n".encode())
        if self.chan is not None:
            with contextlib.suppress(OSError, asyncssh.Error):
                self.chan.exit(code)


class RejectedSession(_BaseSession):
    """Explains why the node is full, then hangs up. No process is spawned."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.chan = None

    def pty_requested(
        self,
        term_type: str,
        term_size: tuple[int, int, int, int],
        term_modes: Mapping[int, int],
    ) -> bool:
        """Accept so the message renders nicely."""
        return True

    def exec_requested(self, command: str) -> bool:
        """Still no exec."""
        return False

    def subsystem_requested(self, subsystem: str) -> bool:
        """Still no subsystems."""
        return False

    def session_started(self) -> None:
        """Explain and disconnect."""
        self.finish(self.reason, 1)


class PortfolioSession(_BaseSession):
    """Bridges one SSH channel to one sandboxed app process on a PTY."""

    def __init__(self, server: PortfolioServer) -> None:
        super().__init__(server)
        self.session_id = uuid.uuid4().hex[:8]
        self.term: str | None = None
        self.size = (80, 24)
        self.bridge: PtyProcess | None = None
        self.started = time.monotonic()
        self.last_activity = self.started
        self.end_reason = "app_exit"
        self._task: asyncio.Task[None] | None = None
        self._stop_task: asyncio.Future[None] | None = None

    @property
    def gateway(self) -> Gateway:
        """The owning gateway."""
        return self.server.gateway

    def pty_requested(
        self,
        term_type: str,
        term_size: tuple[int, int, int, int],
        term_modes: Mapping[int, int],
    ) -> bool:
        """Remember TERM and the initial window size."""
        self.term = sanitize_term(term_type)
        columns, rows = term_size[0] or 80, term_size[1] or 24
        self.size = (columns, rows)
        return True

    def session_started(self) -> None:
        """Spawn the app in the background."""
        self._task = asyncio.ensure_future(self._run())

    async def _run(self) -> None:
        if self.term is None:
            self.finish("no_pty", 1)
            return
        try:
            from servers.pty_bridge import PtyProcess
        except ImportError:
            self.finish("unsupported", 1)
            return
        columns, rows = self.size
        try:
            self.bridge = await PtyProcess.spawn(
                self.gateway.config.app_argv,
                env=child_environment(self.term, columns, rows),
                cwd=str(ROOT),
                columns=columns,
                rows=rows,
                on_output=self.send,
            )
        except OSError as error:
            log_event("spawn_failed", logging.ERROR, session=self.session_id, error=str(error))
            self.finish("spawn_failed", 1)
            return
        self.gateway.sessions.add(self)
        log_event("session_start", ip=self.server.ip, session=self.session_id, term=self.term)
        watchdog = asyncio.ensure_future(self._watchdog())
        try:
            code = await self.bridge.wait()
        finally:
            watchdog.cancel()
            self.gateway.sessions.discard(self)
        self.send(RESET_TERMINAL)
        log_event(
            "session_end",
            ip=self.server.ip,
            session=self.session_id,
            reason=self.end_reason,
            exit_code=code,
            duration=round(time.monotonic() - self.started, 1),
        )
        self.finish(self.end_reason, code if code >= 0 else 1)

    async def _watchdog(self) -> None:
        limits = self.gateway.config.limits
        while True:
            await asyncio.sleep(self.gateway.config.watchdog_interval)
            reason = expiry_reason(time.monotonic(), self.started, self.last_activity, limits)
            if reason is not None:
                await self.stop(reason)
                return

    async def stop(self, reason: str) -> None:
        """Terminate the app process, recording why."""
        if self.bridge is not None and self.bridge.process.returncode is None:
            self.end_reason = reason
            await self.bridge.terminate()

    def data_received(self, data: bytes, datatype: int | None) -> None:
        """Keystrokes from the client go to the app."""
        self.last_activity = time.monotonic()
        if self.bridge is not None:
            self.bridge.write(data)

    def terminal_size_changed(self, width: int, height: int, pixwidth: int, pixheight: int) -> None:
        """Forward window resizes to the PTY (and SIGWINCH the app)."""
        self.size = (width or self.size[0], height or self.size[1])
        if self.bridge is not None:
            self.bridge.resize(*self.size)

    def pause_writing(self) -> None:
        """Back-pressure: stop reading app output."""
        if self.bridge is not None:
            self.bridge.pause_reading()

    def resume_writing(self) -> None:
        """Resume reading app output."""
        if self.bridge is not None:
            self.bridge.resume_reading()

    def eof_received(self) -> bool:
        """Client closed its input: end the session."""
        self._stop_task = asyncio.ensure_future(self.stop("client_eof"))
        return False

    def connection_lost(self, exc: Exception | None) -> None:
        """Client went away: make sure the app process dies too."""
        self.chan = None
        self._stop_task = asyncio.ensure_future(self.stop("client_closed"))


async def serve(config: GatewayConfig) -> None:
    """Run until SIGINT/SIGTERM, then terminate all sessions."""
    gateway = Gateway(config)
    acceptor = await gateway.start()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    log_event("server_stop")
    acceptor.close()
    await gateway.shutdown()
    await acceptor.wait_closed()


def main() -> int:
    """Entry point."""
    configure_logging()
    if os.name == "nt":
        log_event("unsupported_platform", logging.ERROR, detail=MESSAGES["unsupported"])
        return 1
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        log_event("running_as_root", logging.WARNING, detail="run the gateway as a non-root user")
    asyncio.run(serve(GatewayConfig.from_env(os.environ)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
