import os
import re

from aiohttp.test_utils import TestClient, TestServer

from servers.web import STATICS, TEMPLATES, SnaizerWebServer, build_command, ssh_command


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


def test_ssh_command():
    assert ssh_command("https://snaizer.example:443", 2222) == "ssh -p 2222 guest@snaizer.example"
    assert ssh_command("https://snaizer.example", 22) == "ssh guest@snaizer.example"
    assert ssh_command("https://snaizer.example", 0) == ""


async def test_page_hides_ssh_hint_when_there_is_no_gateway():
    server = make_server(public_url="https://snaizer.example", ssh_port=0)
    async with TestClient(TestServer(await server._make_app())) as client:
        html = await (await client.get("/")).text()
    assert "ssh " not in html and "from a terminal" not in html


async def test_page_uses_local_font_and_ssh_hint():
    server = make_server(public_url="https://snaizer.example", ssh_port=22)
    async with TestClient(TestServer(await server._make_app())) as client:
        html = await (await client.get("/")).text()
        regular = await client.get("/assets/fonts/MartianMono.ttf")
        condensed = await client.get("/assets/fonts/MartianMono-Condensed.ttf")
    assert "fonts.googleapis.com" not in html
    assert '"MartianMono.ttf"' in html and '"MartianMono-Condensed.ttf"' in html
    assert "ssh guest@snaizer.example" in html
    assert regular.status == 200 and condensed.status == 200


async def test_page_is_set_up_for_phones():
    server = make_server(public_url="https://snaizer.example")
    async with TestClient(TestServer(await server._make_app())) as client:
        html = await (await client.get("/")).text()
    assert "viewport-fit=cover" in html
    assert "snaizer:keyboard/" in html  # the app's keyboard requests are intercepted
    assert "visualViewport" in html  # resize above the phone keyboard
    assert '"touchmove"' in html  # swipe to scroll
    assert "font-size: 16px !important" in html  # no iOS zoom on focus


async def test_session_cap_returns_503():
    server = make_server(max_sessions=0)
    async with TestClient(TestServer(await server._make_app())) as client:
        response = await client.get("/ws")
    assert response.status == 503
