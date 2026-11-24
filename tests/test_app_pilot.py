"""End-to-end UI tests driven by Textual's Pilot."""

import pytest
from conftest import screen_text
from textual.widgets import Button, Input

from snaizer_net.navigation import SECTIONS
from snaizer_net.screens.boot import BootScreen
from snaizer_net.screens.login import LoginScreen
from snaizer_net.screens.main import MainScreen
from snaizer_net.screens.overlays import HelpScreen, MatrixScreen, TooSmallScreen
from snaizer_net.widgets.nav import NavItem
from snaizer_net.widgets.project_card import ProjectCard

EXPECTED = {
    "profile": ["Mohammed Tchichi", "Master's student in AI & IoT", "TOP SECRET // EYES ONLY"],
    "education": ["Master d'Excellence in Artificial", "B.Sc. Artificial Intelligence"],
    "skills": ["Python (OOP)", "relative proficiency", "Programming"],
    "projects": ["Data-Driven Pentesting Framework", "CLASSIFIED", "Currency Converter"],
    "awards": ["1st Place", "Innovation Camp", "3rd Place", "ENSA Kenitra"],
    "experience": ["Sales Advisor", "Decathlon, Kenitra", "Freelance IT Customer Support"],
    "contact": ["mohammedtchichi03@gmail.com", "https://github.com/Sn4iZer"],
    "terminal": ["simulated node"],
    "timeline": ["Jun–Jul 2026", "Sales Advisor", "2026–present"],
}


async def wait_for_screen(pilot, screen_type, timeout: float = 10.0) -> None:
    waited = 0.0
    while not isinstance(pilot.app.screen, screen_type) and waited < timeout:
        await pilot.pause(0.1)
        waited += 0.1
    assert isinstance(pilot.app.screen, screen_type), type(pilot.app.screen)
    await pilot.pause(0.1)  # let the new screen finish mounting


async def login(pilot, user: str, password: str) -> None:
    screen = pilot.app.screen
    screen.query_one("#login-user", Input).value = user
    screen.query_one("#login-pass", Input).value = password
    screen.query_one("#login-pass", Input).focus()
    await pilot.press("enter")


@pytest.mark.parametrize("size", [(80, 24), (200, 50)])
async def test_full_flow_and_every_tab_renders(make_app, size):
    app = make_app()
    async with app.run_test(size=size) as pilot:
        await wait_for_screen(pilot, BootScreen)
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await login(pilot, "case", "wintermute")
        await wait_for_screen(pilot, MainScreen)
        assert app.screen.has_class("-narrow") is (size[0] < 100)
        for spec in SECTIONS[:9]:
            app.screen.set_focus(None)
            await pilot.press(spec.key)
            await pilot.pause(0.1)
            assert app.screen.current == spec.id
            text = screen_text(app)
            for needle in EXPECTED[spec.id]:
                assert needle in text, f"{needle!r} missing from {spec.id} at {size}"


async def test_animated_boot_finishes_by_itself(make_app):
    app = make_app(animations=True)
    async with app.run_test(size=(100, 30)) as pilot:
        await wait_for_screen(pilot, LoginScreen, timeout=12)
        assert "NEURAL-LINK AUTHENTICATION" in screen_text(app)


async def test_login_empty_fields_denied(make_app):
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await login(pilot, "", "")
        await pilot.pause(0.1)
        assert "biometric mismatch" in screen_text(app)
        assert isinstance(app.screen, LoginScreen)


async def test_login_trace_joke_then_retry(make_app):
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await login(pilot, "neo", "1234")
        await pilot.pause(0.1)
        text = screen_text(app)
        assert "trace initiated" in text
        assert "3... 2... 1..." in text
        await pilot.pause(0.8)
        assert not app.screen.busy
        await login(pilot, "neo", "1234")
        await wait_for_screen(pilot, MainScreen)


async def test_login_guest_hint(make_app):
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await login(pilot, "guest", "guest")
        await pilot.pause(0.2)
        assert "any credentials work, runner" in screen_text(app)
        await wait_for_screen(pilot, MainScreen)
        assert app.admin is False


@pytest.mark.parametrize("user", ["snaizer", "admin"])
async def test_login_admin_badge_and_extra_tab(make_app, user):
    app = make_app()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await login(pilot, user, "x")
        await wait_for_screen(pilot, MainScreen)
        assert app.admin
        assert "ADMIN" in screen_text(app)
        await pilot.press("0")
        await pilot.pause(0.1)
        assert app.screen.current == "blackice"
        assert "FICTION" in screen_text(app)


async def test_non_admin_has_no_blackice(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("0")
        assert app.screen.current == "profile"
        assert "black-ice" not in screen_text(app)


async def test_keyboard_navigation(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        screen = app.screen
        await pilot.press("down")
        assert screen.current == "education"
        await pilot.press("j")
        assert screen.current == "skills"
        await pilot.press("k")
        assert screen.current == "education"
        await pilot.press("tab")
        assert screen.current == "skills"
        await pilot.press("up", "up", "up")
        assert screen.current == "timeline"  # wraps around
        await pilot.press("1")
        assert screen.current == "profile"


async def test_mouse_navigation_sidebar_and_tabstrip(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        target = next(i for i in app.screen.query("#sidebar NavItem") if i.spec.id == "awards")
        await pilot.click(target)
        assert app.screen.current == "awards"
        await pilot.resize_terminal(85, 30)
        await pilot.pause(0.2)
        assert app.screen.has_class("-narrow")
        tab = next(i for i in app.screen.query("#tabstrip NavItem") if i.spec.id == "contact")
        await pilot.click(tab)
        assert app.screen.current == "contact"


async def test_projects_dossier_expand(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("4")
        card = app.screen.query_one(ProjectCard)
        assert card.index == 1 and not card.expanded
        await pilot.press("down")
        assert card.project.title == "Airbnb NYC Price Prediction Platform"
        await pilot.press("j")
        assert card.index == 3
        await pilot.press("enter")
        assert card.expanded
        await pilot.press("enter")
        assert not card.expanded


async def test_terminal_commands_through_the_ui(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("8")
        await pilot.press(*"whoami", "enter")
        await pilot.pause(0.1)
        assert "visitor on Mohammed Tchichi's node" in screen_text(app)
        await pilot.press(*"theme toxic-green", "enter")
        await pilot.pause(0.1)
        assert app.theme == "toxic-green"
        await pilot.press(*"q", "enter")  # typing q in the shell must not quit
        assert app.is_running
        await pilot.press(*"neo", "tab")
        assert app.screen.query_one("#shell-input", Input).value == "neofetch "
        await pilot.press("enter", "up")
        assert app.screen.query_one("#shell-input", Input).value == "neofetch"
        await pilot.press("escape")
        assert app.focused is None
        await pilot.press("2")
        assert app.screen.current == "education"


async def test_shell_exit_quits(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("8", *"exit", "enter")
        await pilot.pause(0.2)
        assert not app.is_running


async def test_help_matrix_and_quit(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("question_mark")
        assert isinstance(app.screen, HelpScreen)
        assert "OPERATOR MANUAL" in screen_text(app)
        await pilot.press("escape")
        await pilot.press("m")
        assert isinstance(app.screen, MatrixScreen)
        await pilot.press("x")
        assert isinstance(app.screen, MainScreen)
        await pilot.press("q")
        await pilot.pause(0.1)
        assert not app.is_running


async def test_ctrl_c_quits_from_login(make_app):
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        await wait_for_screen(pilot, LoginScreen)
        await pilot.press("ctrl+c")
        await pilot.pause(0.1)
        assert not app.is_running


async def test_too_small_overlay(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause(0.1)
        await pilot.resize_terminal(36, 16)
        await pilot.pause(0.2)
        assert isinstance(app.screen, TooSmallScreen)
        assert not app.motion_enabled
        text = screen_text(app)
        assert "now 36x16" in text and "40x18" in text
        await pilot.resize_terminal(46, 20)  # a phone is fine
        await pilot.pause(0.2)
        assert isinstance(app.screen, MainScreen)
        assert app.motion_enabled


async def test_contact_buttons_depend_on_mode(make_app):
    local = make_app(skip_intro=True)
    async with local.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        ids = {b.id for b in local.screen.query(Button)}
        assert ids == {"decrypt-phone", "copy-email", "copy-github"}

    web = make_app(skip_intro=True, mode="web")
    async with web.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("7")
        opened: list[str] = []
        web.open_url = lambda url, new_tab=True: opened.append(url)
        await pilot.click("#open-github")
        assert opened == ["https://github.com/Sn4iZer"]


@pytest.mark.parametrize(
    ("colors", "term", "expected"),
    [
        ("16", "xterm-256color", "neon-16"),
        ("auto", "linux", "neon-16"),
        ("auto", "xterm-256color", "neon-night"),
        ("truecolor", "linux", "neon-night"),
    ],
)
async def test_color_depth_fallback(make_app, monkeypatch, colors, term, expected):
    monkeypatch.setenv("TERM", term)
    monkeypatch.delenv("COLORTERM", raising=False)
    app = make_app(skip_intro=True, colors=colors)
    assert app.theme == expected


async def test_nav_items_cover_visible_sections(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        ids = [item.spec.id for item in app.screen.query("#sidebar NavItem").results(NavItem)]
        assert ids == [spec.id for spec in SECTIONS if not spec.admin_only]
