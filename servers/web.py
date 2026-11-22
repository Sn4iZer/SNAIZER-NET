"""Serve SNAIZER//NET in the browser with textual-serve.

Environment:
    HOST              bind address (default 0.0.0.0)
    PORT              bind port (default 8000)
    PUBLIC_URL        public base URL, e.g. https://snaizer.example.com.
                      When unset, it is derived from each request (honoring
                      X-Forwarded-Proto / X-Forwarded-Host from Caddy).
    WEB_MAX_SESSIONS  concurrent browser sessions (default 50)
    SSH_PUBLIC_PORT   SSH port advertised on the page (default 2222)
"""

import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import aiohttp_jinja2
import textual_serve
from aiohttp import web
from textual_serve.server import Server

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = Path(__file__).resolve().parent / "web_templates"
ASSETS = Path(__file__).resolve().parent / "web_static"
STATICS = Path(textual_serve.__file__).resolve().parent / "static"


def ssh_command(public_url: str, ssh_port: int) -> str:
    """The ``ssh`` line shown on the page, e.g. ``ssh -p 2222 guest@example.com``."""
    host = urlsplit(public_url).hostname or "localhost"
    port = "" if ssh_port == 22 else f"-p {ssh_port} "
    return f"ssh {port}guest@{host}"


class SnaizerWebServer(Server):
    """textual-serve with a themed page, per-request URLs and a session cap."""

    def __init__(
        self, *args: Any, max_sessions: int = 50, ssh_port: int = 2222, **kwargs: Any
    ) -> None:
        self.derive_url = kwargs.get("public_url") is None
        super().__init__(*args, **kwargs)
        self.max_sessions = max_sessions
        self.ssh_port = ssh_port
        self.active_sessions = 0

    async def _make_app(self) -> web.Application:
        """Add ``/assets`` (our font) next to textual-serve's own routes."""
        app = await super()._make_app()
        app.router.add_static("/assets", ASSETS, name="assets")
        return app

    async def handle_index(self, request: web.Request) -> web.Response:
        """Render the page; derive public URLs from the request when not configured."""
        if self.derive_url:
            proto = request.headers.get("X-Forwarded-Proto", request.scheme)
            host = request.headers.get("X-Forwarded-Host", request.host)
            self.public_url = f"{proto}://{host}"
        # The base handler is wrapped by @aiohttp_jinja2.template; call the
        # undecorated function to get its context and add our own fields.
        context: dict[str, Any] = await Server.handle_index.__wrapped__(self, request)
        context["ssh_command"] = ssh_command(self.public_url, self.ssh_port)
        return aiohttp_jinja2.render_template("app_index.html", request, context)

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Spawn one app process per browser tab, up to ``max_sessions``."""
        if self.active_sessions >= self.max_sessions:
            raise web.HTTPServiceUnavailable(text="SNAIZER//NET is at capacity, retry soon.")
        self.active_sessions += 1
        try:
            return await super().handle_websocket(request)
        finally:
            self.active_sessions -= 1


def build_command(python: str = sys.executable) -> str:
    """Shell command textual-serve runs for each session."""
    quoted = subprocess.list2cmdline([python]) if os.name == "nt" else shlex.quote(python)
    return f"{quoted} -m snaizer_net --mode web"


def main() -> None:
    """Configure from the environment and serve forever."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    public_url = os.environ.get("PUBLIC_URL") or None
    max_sessions = int(os.environ.get("WEB_MAX_SESSIONS", "50"))
    ssh_port = int(os.environ.get("SSH_PUBLIC_PORT", "2222"))

    os.environ["SNAIZER_MODE"] = "web"
    os.environ["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(ROOT), os.environ.get("PYTHONPATH")])
    )
    server = SnaizerWebServer(
        build_command(),
        host=host,
        port=port,
        title="SNAIZER//NET",
        public_url=public_url,
        statics_path=STATICS,
        templates_path=TEMPLATES,
        max_sessions=max_sessions,
        ssh_port=ssh_port,
    )
    server.serve()


if __name__ == "__main__":
    main()
