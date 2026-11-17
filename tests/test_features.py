"""Timeline, counters, sensor feed, project filter, command palette, transitions."""

import pytest
from conftest import screen_text
from textual.command import CommandPalette
from textual.widgets import Input, Sparkline

from snaizer_net.palette import SnaizerCommands
from snaizer_net.screens.login import LoginScreen
from snaizer_net.screens.main import MainScreen
from snaizer_net.sections.panes import ProjectsSection, TimelineSection, filter_tags
from snaizer_net.timeline import build_timeline
from snaizer_net.widgets.counter import CounterStat, format_partial
from snaizer_net.widgets.fake_shell import FakeShellWidget
from snaizer_net.widgets.project_card import ProjectCard
from snaizer_net.widgets.scanline import ScanLine
from snaizer_net.widgets.sensor_panel import SensorPanel


@pytest.mark.parametrize(
    ("value", "fraction", "expected"),
    [
        ("50,000+", 0.5, "25,000+"),
        ("50,000+", 1.0, "50,000+"),
        ("98%", 0.0, "0%"),
        ("2", 1.0, "2"),
        ("3.5x", 0.5, "1.8x"),
        ("N/A", 0.3, "N/A"),
    ],
)
def test_counter_formatting(value, fraction, expected):
    assert format_partial(value, fraction) == expected


def test_timeline_is_newest_first_and_complete(profile):
    entries = build_timeline(profile)
    assert len(entries) == (
        len(profile.education)
        + len(profile.experience)
        + len(profile.projects)
        + len(profile.awards)
    )
    keys = [entry.sort_key for entry in entries]
    assert keys == sorted(keys, reverse=True)
    assert entries[0].title == "Sport Leader"
    assert entries[0].when == "Jun-Jul 2026"
    assert entries[1].kind == "education" and entries[1].when == "2026-2028"


def test_filter_tags_need_two_projects(profile):
    tags = filter_tags(profile.projects)
    assert tags[0] == "Python"
    assert "Kali Linux" not in tags


async def test_profile_counters_and_simulated_sensor_feed(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 45)) as pilot:
        values = [c.value for c in app.screen.query(CounterStat)]
        assert values[:2] == ["2", "5"]
        for _ in range(50):  # counters land on the real value
            await pilot.pause(0.1)
            if "50,000+" in screen_text(app):
                break
        assert "50,000+" in screen_text(app)
        panel = app.screen.query_one(SensorPanel)
        assert "SIMULATED" in panel.border_title
        spark = app.screen.query_one("#spark-temp", Sparkline)
        before = list(spark.data)
        await pilot.pause(1.2)
        assert list(spark.data) != before  # the demo feed is live


async def test_sensor_feed_freezes_without_animations(make_app):
    app = make_app(skip_intro=True, animations=False)
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause(0.1)
        spark = app.screen.query_one("#spark-temp", Sparkline)
        before = list(spark.data)
        await pilot.pause(1.2)
        assert list(spark.data) == before


async def test_timeline_section_reveals_progressively(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("9")
        timeline = app.screen.query_one(TimelineSection)
        await pilot.pause(0.05)
        assert timeline.revealed < len(timeline.entries)  # reveal restarted from zero
        for _ in range(60):
            await pilot.pause(0.1)
            if timeline.revealed == len(timeline.entries):
                break
        assert timeline.revealed == len(timeline.entries)
        assert "E-commerce Founder" in screen_text(app)


async def test_project_tag_filter_cycles(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("4")
        section = app.screen.query_one(ProjectsSection)
        await pilot.press("f")
        await pilot.pause(0.2)
        assert section.active_filter == "Python"
        assert all("Python" in p.tags for p in section.shown_projects)
        assert len(section.shown_projects) == 4
        assert "Python (4)" in screen_text(app)
        await pilot.press("F")
        await pilot.pause(0.2)
        assert section.active_filter is None
        assert len(section.shown_projects) == 5


async def test_shell_open_jumps_to_expanded_dossier(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(140, 45)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("8", *"open 3", "enter")
        await pilot.pause(0.3)
        assert app.screen.current == "projects"
        card = app.screen.query_one(ProjectCard)
        assert card.project.slug == "nids"
        assert card.expanded


async def test_shell_output_streams_with_animations(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("8", *"hack", "enter")
        await pilot.pause(0.05)
        shell = app.screen.query_one(FakeShellWidget)
        assert shell.pending  # still streaming
        await pilot.press(*"whoami", "enter")  # a new command flushes the stream
        assert not shell.pending
        assert "FICTION" in screen_text(app)


async def test_command_palette_navigates(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("slash")
        await pilot.pause(0.2)
        assert isinstance(app.screen, CommandPalette)
        await pilot.press(*"timeline")
        await pilot.pause(0.5)
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert isinstance(app.screen, MainScreen)
        assert app.screen.current == "timeline"


async def test_command_palette_provider_entries(make_app):
    app = make_app(skip_intro=True, mode="local")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        provider = SnaizerCommands(app.screen)
        texts = [text for text, _, _ in provider.entries()]
        assert "Go to TIMELINE" in texts
        assert "Open dossier: SpaceUIT Educational Platform" in texts
        assert "Theme: synthwave" in texts
        assert "Filter projects: Python" in texts
        assert "Go to BLACK-ICE" not in texts  # admin only
        hits = [hit async for hit in provider.search("synthw")]
        assert hits and "synthwave" in str(hits[0].match_display)


async def test_palette_is_disabled_before_login(make_app):
    app = make_app()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        await pilot.pause(0.3)
        assert isinstance(app.screen, LoginScreen)
        await pilot.press("ctrl+p")
        await pilot.pause(0.2)
        assert isinstance(app.screen, LoginScreen)
        assert app.screen.query_one("#login-user", Input).value == ""


async def test_scanline_sweeps_on_section_change(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        scan = app.screen.query_one(ScanLine)
        assert not scan.display
        await pilot.press("2")
        await pilot.pause(0.05)
        assert scan.display
        for _ in range(40):
            await pilot.pause(0.1)
            if not scan.display:
                break
        assert not scan.display


async def test_toggle_animations_at_runtime(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        app.toggle_animations()
        assert not app.motion_enabled
        await pilot.press("2")
        await pilot.pause(0.1)
        assert not app.screen.query_one(ScanLine).display
        app.toggle_animations()
        assert app.motion_enabled
