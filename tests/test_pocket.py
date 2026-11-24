"""The phone ("pocket") layout used by the web build on small screens."""

import pytest
from conftest import screen_text
from test_app_pilot import EXPECTED

from snaizer_net.app import KEYBOARD_URL
from snaizer_net.navigation import SECTIONS
from snaizer_net.overwatch import STACK_INDENT, layout, span, wrap_cells
from snaizer_net.screens.boot import BootScreen
from snaizer_net.screens.login import LoginScreen
from snaizer_net.screens.main import MainScreen
from snaizer_net.screens.overlays import HelpScreen, MenuScreen
from snaizer_net.screens.overwatch import OverwatchScreen
from snaizer_net.widgets.glitch_label import GlitchBanner

PHONE = (46, 38)


def walkthrough_ready(app) -> bool:
    return isinstance(app.screen, OverwatchScreen) and bool(app.screen.query("#ow-stage"))


async def wait_for(pilot, predicate, timeout: float = 10.0) -> None:
    waited = 0.0
    while not predicate() and waited < timeout:
        await pilot.pause(0.1)
        waited += 0.1
    assert predicate()


async def test_pocket_class_follows_the_width(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        assert app.pocket
        assert app.screen.query_one("#dock").display
        assert not app.screen.query_one("#key-hints").display
        await pilot.resize_terminal(120, 40)
        await pilot.pause(0.2)
        assert not app.pocket
        assert not app.screen.query_one("#dock").display


async def test_dock_walks_through_every_section(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        screen = app.screen
        assert "education ›" in screen_text(app)  # labelled with the next section
        for spec in SECTIONS[1:9]:
            await pilot.click("#dock-next")
            await pilot.pause(0.15)
            assert screen.current == spec.id
            needle = EXPECTED[spec.id][0]  # later needles may wrap on a phone
            assert needle in screen_text(app), f"{needle!r} missing from {spec.id} on a phone"
        await pilot.click("#dock-next")  # wraps around
        assert screen.current == "profile"
        await pilot.click("#dock-prev")
        assert screen.current == "timeline"


async def test_menu_jumps_to_a_section_and_runs_actions(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#dock-menu")
        await pilot.pause(0.2)
        assert isinstance(app.screen, MenuScreen)
        assert "Degrees, newest first." in screen_text(app)
        contact = next(i for i in app.screen.query(".menu-item") if i.choice == "contact")
        await pilot.click(contact)
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
        assert app.screen.current == "contact"
        await pilot.click("#dock-menu")
        await pilot.pause(0.2)
        help_action = next(i for i in app.screen.query(".menu-action") if i.choice == "action:help")
        await pilot.click(help_action)
        await wait_for(pilot, lambda: isinstance(app.screen, HelpScreen))
        assert "swipe to scroll" in screen_text(app)


async def test_menu_closes_without_choosing(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#dock-menu")
        await pilot.pause(0.2)
        await pilot.click(".menu-close")
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
        assert app.screen.current == "profile"


async def test_boot_and_login_fit_a_phone(make_app):
    app = make_app(animations=False)
    async with app.run_test(size=PHONE) as pilot:
        await wait_for(pilot, lambda: isinstance(app.screen, BootScreen))
        await pilot.pause(0.2)
        logo = app.screen.query_one(GlitchBanner)
        assert logo.layout_name == "stacked"  # SNAIZER over //NET
        assert "tap to skip" in screen_text(app)
        assert "[  " not in screen_text(app)  # no timestamp column on phones
        await pilot.click()
        await wait_for(pilot, lambda: isinstance(app.screen, LoginScreen))
        await pilot.pause(0.2)
        text = screen_text(app)
        assert "RESTRICTED NODE" in text
        assert "tap a field to type" in text
        assert "TAB switch field" not in text


async def test_banner_falls_back_to_spaced_text_when_very_narrow(make_app):
    app = make_app(animations=False)
    async with app.run_test(size=(40, 24)) as pilot:
        await wait_for(pilot, lambda: isinstance(app.screen, BootScreen))
        await pilot.pause(0.2)
        assert app.screen.query_one(GlitchBanner).layout_name == "spaced"
        assert "S N A I Z E R" in screen_text(app)


async def test_walkthrough_has_tap_controls(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        app.screen.query_one("#classified").scroll_visible(animate=False)
        await pilot.pause(0.2)
        await pilot.click("#classified")
        await wait_for(pilot, lambda: walkthrough_ready(app))
        screen = app.screen
        screen.seek(screen.timeline.starts[1])  # controls are hidden during the breach
        await pilot.pause(0.1)
        await pilot.click("#ow-next")
        assert screen.timeline.locate(screen.elapsed)[0] == 2
        await pilot.click("#ow-pause")
        assert screen.paused
        assert "play" in screen_text(app)
        await pilot.click("#ow-prev")
        assert screen.timeline.locate(screen.elapsed)[0] == 1
        await pilot.click("#ow-exit")
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))


async def test_walkthrough_stacks_long_values_on_phones(make_app):
    app = make_app(skip_intro=True, animations=False)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.pause(0.1)
        app.screen.open_classified()
        await wait_for(pilot, lambda: walkthrough_ready(app))
        screen = app.screen
        screen.paused = True
        contact = next(i for i, s in enumerate(screen.timeline.segments) if s.id == "contact")
        screen.seek(screen.timeline.starts[contact] + 0.1)
        await pilot.pause(0.1)
        assert "mohammedtchichi03@gmail.com" in screen_text(app)  # whole, not hard-cut


async def test_keyboard_requests_follow_text_fields_in_web_mode(make_app):
    app = make_app(mode="web")
    sent: list[str] = []
    app.open_url = lambda url, new_tab=True: sent.append(url)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.click()
        await wait_for(pilot, lambda: isinstance(app.screen, LoginScreen))
        await wait_for(pilot, lambda: sent[-1:] == [f"{KEYBOARD_URL}/on"])
        await pilot.press(*"neo", "enter", *"pw", "enter")
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
        await wait_for(pilot, lambda: sent[-1:] == [f"{KEYBOARD_URL}/off"])
        await pilot.press("8")  # the terminal focuses its prompt
        await wait_for(pilot, lambda: sent[-1:] == [f"{KEYBOARD_URL}/on"])


async def test_no_keyboard_requests_outside_the_browser(make_app):
    app = make_app()
    sent: list[str] = []
    app.open_url = lambda url, new_tab=True: sent.append(url)
    async with app.run_test(size=PHONE) as pilot:
        await pilot.click()
        await wait_for(pilot, lambda: isinstance(app.screen, LoginScreen))
        await pilot.pause(0.2)
        assert sent == []


@pytest.mark.parametrize("width", range(12, 80))
def test_wrapping_always_terminates_and_keeps_every_character(width):
    line = [span("2026–present  "), span("Master d'Excellence in Artificial Intelligence & IoT")]
    cells = wrap_cells([(c, "text", "") for text, _, _ in line for c in text], width, indent=14)
    original = "".join(text for text, _, _ in line).replace(" ", "")
    assert "".join(c[0] for row in cells for c in row).replace(" ", "") == original
    assert all(len(row) <= width for row in cells)


def test_layout_stacks_values_under_labels():
    facts = [(span("email".ljust(10)), span("mohammedtchichi03@gmail.com"))]
    stacked = ["".join(c[0] for c in row) for row in layout(facts, 34, stack=True)]
    assert stacked == ["email", " " * STACK_INDENT + "mohammedtchichi03@gmail.com"]
    side_by_side = ["".join(c[0] for c in row) for row in layout(facts, 60, stack=True)]
    assert side_by_side == ["email     mohammedtchichi03@gmail.com"]
