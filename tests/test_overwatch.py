"""The classified file and the surveillance walkthrough it opens."""

from itertools import pairwise
from pathlib import Path

import pytest
import yaml
from conftest import screen_text
from textual.content import Content
from textual.widgets import Input

from snaizer_net.content import OVERWATCH_SCENES, ContentError, load_lore
from snaizer_net.overwatch import (
    SECRET,
    Timeline,
    build_segments,
    cells_markup,
    fill,
    layout,
    reveal,
    span,
    to_cells,
    wrap_cells,
)
from snaizer_net.screens.main import MainScreen
from snaizer_net.screens.overwatch import OverwatchScreen, alarm_flash
from snaizer_net.widgets.classified import ClassifiedButton


def plain_facts(segments) -> str:
    return "\n".join(
        "".join(text for text, color, _ in line if color != SECRET)
        for segment in segments
        for line in segment.facts
    )


# -- the walkthrough as data ---------------------------------------------------


def test_segments_play_in_order_for_about_a_minute(profile, lore):
    segments = build_segments(profile, lore)
    assert [s.id for s in segments] == ["breach", "online", *OVERWATCH_SCENES, "ending"]
    assert 50 <= Timeline(segments).total <= 65


def test_every_fact_comes_from_the_profile(profile, lore):
    segments = build_segments(profile, lore)
    text = plain_facts(segments)
    ident, contact = profile.identity, profile.contact
    expected = [ident.name, ident.handle, ident.title, ident.location, contact.email]
    expected.append(contact.github_url)
    expected += [e.degree for e in profile.education] + [e.institution for e in profile.education]
    expected += [skill.name for cat in profile.skills for skill in cat.skills]
    expected += [f"{lang.name} ({lang.level})" for lang in profile.languages]
    expected += [p.title for p in profile.projects] + [p.kind for p in profile.projects]
    expected += [a.title for a in profile.awards] + [a.description for a in profile.awards]
    expected += [e.title for e in profile.experience] + [e.organization for e in profile.experience]
    missing = [fact for fact in expected if fact not in text]
    assert missing == []
    contact_scene = next(s for s in segments if s.id == "contact")
    assert contact_scene.secret == "+212 627 777 113"
    assert "627" not in text  # the phone only exists behind the decode effect


def test_narration_is_filled_from_real_counts(profile, lore):
    by_id = {s.id: s for s in build_segments(profile, lore)}
    assert "alias: Sn4iZer" in by_id["identity"].narration
    assert f"operations on record: {len(profile.projects)}" in by_id["projects"].narration
    assert any("OVERWATCH-7" in line for line in by_id["online"].narration)


def test_fill_leaves_unknown_placeholders_alone():
    assert fill("{nope} {handle}", {"handle": "x"}) == "{nope} x"
    assert fill("{0} {", {}) == "{0} {"


def test_wrap_keeps_width_style_and_hanging_indent():
    cells = to_cells([span("Tools".ljust(8), "cyan"), span("aaa bbb ccc ddd eee", "dim")])
    rows = wrap_cells(cells, 16, indent=8)
    assert all(len(row) <= 16 for row in rows)
    assert "".join(c[0] for c in rows[1]).startswith(" " * 8)
    assert {c[1] for c in rows[0][:5]} == {"cyan"}
    assert len(layout([[span("x" * 50)]], 20)) == 3


def test_reveal_types_across_lines():
    rows = [to_cells([span("abc")]), to_cells([span("defg")])]
    assert ["".join(c[0] for c in row) for row in reveal(rows, 5)] == ["abc", "de"]
    assert reveal(rows, 0) == []


def test_cells_markup_escapes_and_renders_secret():
    cells = to_cells([span("[$neon-danger]x", "text"), span("###", SECRET)])
    markup = cells_markup(cells, secret=lambda n: "Z" * n)
    assert Content.from_markup(markup).plain == "[$neon-danger]xZZZ"


def test_timeline_locates_segments(profile, lore):
    timeline = Timeline(build_segments(profile, lore))
    assert timeline.locate(0) == (0, 0.0)
    index, local = timeline.locate(timeline.starts[3] + 1.5)
    assert (index, local) == (3, pytest.approx(1.5))
    assert timeline.locate(10_000)[0] == len(timeline.segments) - 1
    assert timeline.scene_number(2) == 1
    assert timeline.scene_number(0) == 0


def test_alarm_flashes_three_times_slowly():
    samples = [alarm_flash(t / 100) for t in range(400)]
    rises = sum(1 for a, b in pairwise(samples) if b and not a)
    assert samples[0] and rises + 1 == 3
    assert not any(samples[100:])  # flashing stops after one second


def test_lore_must_narrate_every_scene(content_copy: Path):
    path = content_copy / "lore.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    del data["overwatch"]["narration"]["skills"]
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ContentError, match=r"narration\.skills"):
        load_lore(path)


# -- in the app -----------------------------------------------------------------


async def wait_for(pilot, predicate, timeout: float = 10.0) -> None:
    waited = 0.0
    while not predicate() and waited < timeout:
        await pilot.pause(0.1)
        waited += 0.1
    assert predicate()


async def test_button_opens_the_walkthrough_and_then_disappears(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.2)
        assert "TOP SECRET // EYES ONLY" in screen_text(app)
        app.overwatch_speed = 60
        await pilot.click("#classified")
        await pilot.pause(0.1)
        assert isinstance(app.screen, OverwatchScreen)
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
        assert app.classified_opened
        await wait_for(pilot, lambda: not list(app.screen.query(ClassifiedButton)))
        assert "TOP SECRET" not in screen_text(app)


async def test_every_scene_shows_the_real_data(make_app, profile):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(200, 50)) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#classified")
        await pilot.pause(0.1)
        screen = app.screen
        screen.paused = True
        timeline = screen.timeline
        seen = ""
        for index, segment in enumerate(timeline.segments):
            # the ending card shows before its last second ("TERMINATED")
            point = 0.6 if segment.kind == "ending" else 0.93
            screen.seek(timeline.starts[index] + segment.duration * point)
            await pilot.pause(0.05)
            seen += screen_text(app)
        for fact in (
            profile.identity.name,
            "Master d'Excellence in Artificial Intelligence & IoT",
            "Python (OOP)",
            *(project.title for project in profile.projects),
            *(award.title for award in profile.awards),
            *(exp.title for exp in profile.experience),
            profile.contact.email,
            "+212 627 777 113",
        ):
            assert fact in seen, fact
        assert "SHOULD NOT HAVE BEEN OPENED" in seen
        assert "contact the subject for an interview" in seen
        assert "every fact is real" in seen
        assert "◉ LOCK" in seen


async def test_controls_pause_skip_and_escape(make_app):
    app = make_app(skip_intro=True, animations=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#classified")
        await pilot.pause(0.2)
        screen = app.screen
        await pilot.press("right")  # skip the breach (it hides the header)
        assert screen.timeline.locate(screen.elapsed)[0] == 1
        await pilot.press("space")
        frozen = screen.elapsed
        await pilot.pause(0.4)
        assert screen.paused and screen.elapsed == frozen
        assert "PAUSED" in screen_text(app)
        await pilot.press("right", "right")
        assert screen.timeline.locate(screen.elapsed)[0] == 3
        await pilot.press("left")
        assert screen.timeline.locate(screen.elapsed)[0] == 2
        await pilot.press("escape")
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
        # gone even after Esc
        await wait_for(pilot, lambda: not list(app.screen.query(ClassifiedButton)))


async def test_tab_then_enter_opens_the_file(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.press("tab")
        assert isinstance(app.focused, ClassifiedButton)
        assert app.screen.current == "profile"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert isinstance(app.screen, OverwatchScreen)


async def test_tab_moves_on_once_the_file_is_gone(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#classified")
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.2)
        await pilot.press("tab")
        assert app.screen.current == "education"


async def test_shell_command_replays_after_the_button_is_gone(make_app):
    app = make_app(skip_intro=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#classified")
        await pilot.pause(0.1)
        await pilot.press("escape")
        await pilot.pause(0.2)
        await pilot.press("8", *"classified", "enter")
        await pilot.pause(0.2)
        assert isinstance(app.screen, OverwatchScreen)
        await pilot.press("escape")
        await pilot.pause(0.2)
        assert app.screen.query_one("#shell-input", Input).value == ""


async def test_without_animations_it_still_plays_and_fits_80x24(make_app):
    app = make_app(skip_intro=True, animations=False)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(0.1)
        await pilot.click("#classified")
        await pilot.pause(0.1)
        screen = app.screen
        screen.paused = True
        contact = next(i for i, s in enumerate(screen.timeline.segments) if s.id == "contact")
        screen.seek(screen.timeline.starts[contact] + 0.1)  # no effects: shown at once
        await pilot.pause(0.05)
        assert "+212 627 777 113" in screen_text(app)
        skills = next(i for i, s in enumerate(screen.timeline.segments) if s.id == "skills")
        screen.seek(screen.timeline.starts[skills] + 0.1)
        await pilot.pause(0.05)
        assert "Arabic (Native)" in screen_text(app)  # last row still fits
        screen.paused = False
        screen.speed = 200
        await wait_for(pilot, lambda: isinstance(app.screen, MainScreen))
