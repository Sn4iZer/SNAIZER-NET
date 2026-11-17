import os
import re

from aiohttp.test_utils import TestClient, TestServer

from servers.web import STATICS, TEMPLATES, SnaizerWebServer, build_command


def make_server(**kwargs) -> SnaizerWebServer:
    return SnaizerWebServer(
        build_command(),
        title="SNAIZER//NET",
        statics_path=STATICS,
        templates_path=TEMPLATES,
        **kwargs,
    )


def test_build_command_runs_web_mode():
    command = build_command("/opt/venv/bin/python")
    assert command.endswith("-m snaizer_net --mode web")
    if os.name != "nt":
        assert build_command("/odd path/python").startswith("'/odd path/python'")


async def test_index_is_themed_and_derives_urls_from_proxy_headers():
    server = make_server()
    async with TestClient(TestServer(await server._make_app())) as client:
        response = await client.get(
            "/", headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "snaizer.example"}
        )
        html = await response.text()
    assert response.status == 200
    assert "<title>SNAIZER//NET</title>" in html
    assert 'rel="icon"' in html
    assert "#0a0a12" in html
    assert re.search(r'data-session-websocket-url="wss://snaizer\.example/ws"', html)


async def test_public_url_overrides_request():
    server = make_server(public_url="https://fixed.example")
    async with TestClient(TestServer(await server._make_app())) as client:
        html = await (await client.get("/")).text()
    assert "wss://fixed.example/ws" in html


async def test_session_cap_returns_503():
    server = make_server(max_sessions=0)
    async with TestClient(TestServer(await server._make_app())) as client:
        response = await client.get("/ws")
    assert response.status == 503
