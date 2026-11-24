"""The classified-file walkthrough, played like a video.

An alarm, a breach, then a surveillance AI compiling the subject's profile.
Playback is a clock (``elapsed``) plus a pure render of "where are we now", so
pause, skip and seek are just changes to the clock.
"""

import random
import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from snaizer_net.assets.ascii import render_banner
from snaizer_net.config import ANIM_FPS
from snaizer_net.content import Lore, Profile
from snaizer_net.markup import tint
from snaizer_net.overwatch import (
    Segment,
    Timeline,
    build_segments,
    cells_markup,
    layout,
    reveal,
)
from snaizer_net.widgets.decrypt_text import decode_markup
from snaizer_net.widgets.motion import motion_enabled
from snaizer_net.widgets.scanline import ScanLine

LOCK_END = 0.15
"""Fraction of a scene spent locking the reticle onto the data."""
TYPE_END = 0.75
"""Fraction of a scene by which all facts are typed in."""
DECODE_START, DECODE_END = 0.55, 0.85
"""Window in which the sealed phone number decodes."""
FLASH_SECONDS, FLASH_PERIOD = 1.0, 0.4
"""Red flashes: on for half of each 0.4 s period, three times (2.5 per second)."""
TEARS_START, BLACKOUT_START, FOLLOW_START = 2.6, 3.6, 2.0
COUNTDOWN_START, COUNTDOWN_FROM = 2.0, 5
SHORT_HEIGHT = 30
"""Below this terminal height the stage drops its vertical padding."""
NOISE = "▓▒░"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def alarm_flash(local: float) -> bool:
    """Is the red alarm flash on ``local`` seconds into the breach? (3 slow flashes)."""
    return local < FLASH_SECONDS and local % FLASH_PERIOD < FLASH_PERIOD / 2


class OverwatchScreen(Screen[None]):
    """Plays the walkthrough; Space pauses, ←/→ skip scenes, Esc leaves."""

    AUTO_FOCUS = ""
    BINDINGS = [
        Binding("space", "toggle_pause", "pause", show=False),
        Binding("left", "skip(-1)", "previous scene", show=False),
        Binding("right", "skip(1)", "next scene", show=False),
        Binding("escape", "leave", "leave", show=False),
    ]

    def __init__(self, profile: Profile, lore: Lore, *, speed: float = 1.0) -> None:
        super().__init__()
        self.profile = profile
        self.lore = lore
        self.speed = speed
        self.timeline = Timeline(build_segments(profile, lore))
        self.elapsed = 0.0
        self.paused = False
        self.closing = False
        self.index = -1
        self._last = time.monotonic()
        self._rng = random.Random()

    # -- lifecycle -------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Header, stage (with a scanline overlay) and footer."""
        yield Static("", id="ow-header")
        with Vertical(id="ow-stage-wrap"):
            yield Static("", id="ow-stage")
            yield ScanLine(color="danger", id="ow-scan")
        yield Static("", id="ow-footer")

    def on_mount(self) -> None:
        """Start the clock (slowly when animations are off: frames are static)."""
        self._last = time.monotonic()
        interval = 1 / ANIM_FPS if self.motion else 0.5
        self.set_interval(interval, self._tick)
        self.render_frame()

    @property
    def motion(self) -> bool:
        """True when animations are allowed."""
        return motion_enabled(self)

    def _tick(self) -> None:
        now = time.monotonic()
        if not self.paused:
            self.elapsed += (now - self._last) * self.speed
        self._last = now
        if self.elapsed >= self.timeline.total:
            self.finish()
            return
        self.render_frame()

    def finish(self) -> None:
        """Close once and hand control back to the HUD."""
        if not self.closing:
            self.closing = True
            self.dismiss()

    # -- controls --------------------------------------------------------

    def action_toggle_pause(self) -> None:
        """Pause or resume playback."""
        self.paused = not self.paused
        self.render_frame()

    def action_skip(self, delta: int) -> None:
        """Jump to the start of the previous/next segment."""
        index, _ = self.timeline.locate(self.elapsed)
        target = index + delta
        if target >= len(self.timeline.segments):
            self.finish()
            return
        self.seek(self.timeline.starts[max(0, target)])

    def action_leave(self) -> None:
        """Esc: stop watching."""
        self.finish()

    def seek(self, seconds: float) -> None:
        """Move the clock to ``seconds`` and redraw."""
        self.elapsed = max(0.0, min(seconds, self.timeline.total - 0.001))
        self.render_frame()

    # -- rendering -------------------------------------------------------

    def render_frame(self) -> None:
        """Draw the current moment of the walkthrough."""
        if self.closing:
            return
        index, local = self.timeline.locate(self.elapsed)
        segment = self.timeline.segments[index]
        if index != self.index:
            self.index = index
            if segment.kind == "scene" and self.motion:
                self.query_one(ScanLine).sweep()
        stage = self.query_one("#ow-stage", Static)
        width = max(20, stage.size.width or self.app.size.width - 4)
        height = max(6, stage.size.height or self.app.size.height - 6)
        flash = self.motion and alarm_flash(local)
        self.set_class(self.app.size.height < SHORT_HEIGHT, "-short")
        self.set_class(segment.kind == "breach", "-breach")
        self.set_class(segment.kind == "breach" and flash, "-alarm")
        terminated = segment.kind == "ending" and local >= segment.duration - 1.0
        stage.set_class(segment.kind == "ending" and not terminated, "-ending")
        if segment.kind == "breach":
            body = self._breach(local, width, height)
        elif segment.kind == "online":
            body = self._online(segment, local, height)
        elif segment.kind == "scene":
            body = self._scene(segment, local, width, height)
        else:
            body = self._ending(segment, local, width, height)
        stage.update(body)
        self.query_one("#ow-header", Static).update(self._header(segment, index))
        self.query_one("#ow-footer", Static).update(self._footer())

    def _header(self, segment: Segment, index: int) -> str:
        ow = self.lore.overwatch
        if self.paused:
            rec = tint("yellow", "▌▌ PAUSED", "bold")
        elif not self.motion or int(self.elapsed * 2) % 2 == 0:
            rec = tint("danger", "◉ REC", "bold")
        else:
            rec = tint("dim", "◉ REC")
        left = f"{rec}  {tint('danger', ow.system, 'bold')} {tint('dim', '// ' + ow.tagline)}"
        number = self.timeline.scene_number(index)
        scenes = len(self.timeline.scenes)
        where = f"SCENE {number}/{scenes} // {segment.title}" if number else segment.id.upper()
        right = (
            f"{tint('dim', 'FILE')} {tint('yellow', ow.file_id)}   {tint('text', where, 'bold')}"
        )
        return f"{left}\n{right}"

    def _footer(self) -> str:
        total = self.timeline.total
        clock = f"{_mmss(self.elapsed)} / {_mmss(total)}"
        hints = "space pause  ←→ skip  esc exit"
        width = max(20, self.app.size.width - 4)
        bar_width = max(10, width - len(clock) - len(hints) - 6)
        filled = round(_clamp(self.elapsed / total) * bar_width)
        bar = tint("danger", "█" * filled) + tint("dim", "░" * (bar_width - filled))
        keys = "  ".join(
            f"{tint('cyan', key, 'bold')} {tint('dim', label)}"
            for key, label in (("space", "pause"), ("←→", "skip"), ("esc", "exit"))
        )
        return f"{bar} {tint('text', clock)}   {keys}"

    def _center(self, rows: list[str], plain_widths: list[int], width: int, height: int) -> str:
        top = max(0, (height - len(rows)) // 2)
        lines = [""] * top
        for row, plain in zip(rows, plain_widths, strict=True):
            lines.append(" " * max(0, (width - plain) // 2) + row)
        return "\n".join(lines)

    def _banner_rows(self, words: tuple[str, ...], width: int) -> list[tuple[str, int]]:
        """Block-letter rows (plain text) for each word, falling back to text."""
        rows: list[tuple[str, int]] = []
        for number, word in enumerate(words):
            if number:
                rows.append(("", 0))
            glyphs = render_banner(word, compact=True)
            if len(glyphs[0]) <= width:
                rows += [(row, len(row)) for row in glyphs]
            else:
                rows.append((word, len(word)))
        return rows

    def _breach(self, local: float, width: int, height: int) -> str:
        ow = self.lore.overwatch
        if not self.motion:
            rows = self._banner_rows(ow.alarm + ow.alarm_follow, width)
            return self._center(
                [tint("danger", text, "bold") for text, _ in rows],
                [size for _, size in rows],
                width,
                height,
            )
        if local >= BLACKOUT_START:
            return ""
        words = ow.alarm if local < FOLLOW_START else ow.alarm_follow
        rows = self._banner_rows(words, width)
        tear = _clamp((local - TEARS_START) / (BLACKOUT_START - TEARS_START))
        styled: list[str] = []
        sizes: list[int] = []
        for text, size in rows:
            if tear and self._rng.random() < tear * 0.7:
                shift = self._rng.randint(1, 8)
                noisy = "".join(
                    self._rng.choice(NOISE) if ch != " " and self._rng.random() < tear else ch
                    for ch in text
                )
                color = self._rng.choice(("cyan", "magenta"))
                styled.append(" " * shift + tint(color, noisy, "bold"))
                sizes.append(size)
            else:
                styled.append(tint("danger", text, "bold"))
                sizes.append(size)
        if tear:
            for _ in range(int(tear * 6)):
                at = self._rng.randrange(len(styled) + 1)
                length = self._rng.randint(width // 4, width)
                noise = "".join(self._rng.choice(NOISE) for _ in range(length))
                styled.insert(at, tint("danger", noise))
                sizes.insert(at, length)
        return self._center(styled, sizes, width, height)

    def _typed_lines(self, lines: tuple[str, ...], progress: float) -> list[str]:
        """Narration lines typed up to ``progress`` (0-1), with a ▸ marker."""
        total = sum(len(line) for line in lines)
        budget = round(total * _clamp(progress)) if self.motion else total
        out = []
        for line in lines:
            if budget <= 0:
                break
            shown = line[:budget]
            budget -= len(line)
            cursor = tint("danger", "▌") if len(shown) < len(line) else ""
            out.append(f"{tint('danger', '▸', 'bold')} {tint('dim', shown)}{cursor}")
        return out

    def _online(self, segment: Segment, local: float, height: int) -> str:
        lines = self._typed_lines(segment.narration, local / (segment.duration * 0.8))
        lines += [""] * (len(segment.narration) - len(lines))
        return _middle(lines, height)

    def _scene(self, segment: Segment, local: float, width: int, height: int) -> str:
        progress = local / segment.duration
        motion = self.motion
        lock = 1.0 if not motion else _clamp(progress / LOCK_END)
        typed = 1.0 if not motion else _clamp((progress - LOCK_END) / (TYPE_END - LOCK_END))
        decode = (
            1.0 if not motion else _clamp((progress - DECODE_START) / (DECODE_END - DECODE_START))
        )
        narration = self._typed_lines(segment.narration, progress / LOCK_END)

        rows = layout(segment.facts, max(18, min(width - 6, 74)))
        # the reticle hugs the data it locks onto
        inner = max(30, min(width - 4, max(len(row) for row in rows) + 4))
        # rows left for facts: minus narration, the two reticle rows and a spacer
        spacer = 1 if height - len(segment.narration) - 3 >= len(rows) else 0
        room = height - len(segment.narration) - 2 - spacer
        pad_v = 0 if not motion else round((1 - lock) * 2)
        pad_v = max(0, min(pad_v, (room - len(rows)) // 2))
        rows = rows[: max(1, room - 2 * pad_v)]
        pad_h = 0 if not motion else round((1 - lock) * 8)
        box = min(width, inner + 2 * pad_h)
        left = " " * max(0, (width - box) // 2)
        locked = lock >= 1.0
        color = "danger" if locked else "cyan"
        label = tint("danger", " ◉ LOCK ", "bold reverse") if locked else ""
        gap = " " * max(0, box - 4 - (8 if locked else 0))
        blank = " " * max(0, box - 4)
        top = f"{left}{tint(color, '┌─', 'bold')}{label}{gap}{tint(color, '─┐', 'bold')}"
        bottom = f"{left}{tint(color, '└─', 'bold')}{blank}{tint(color, '─┘', 'bold')}"

        total_cells = sum(len(row) for row in rows)
        shown = reveal(rows, round(total_cells * typed)) if locked else []
        secret_locked = round(len(segment.secret) * decode)

        def secret(count: int) -> str:
            if decode <= 0:
                return tint("dim", "".join(self._rng.choice(NOISE) for _ in range(count)))
            return decode_markup(segment.secret[:count], secret_locked, self._rng)

        indent = left + " " * (pad_h + 2)
        body = [""] * pad_v
        for number in range(len(rows)):
            if number < len(shown):
                line = cells_markup(shown[number], secret)
                typing = number == len(shown) - 1 and typed < 1.0
                body.append(indent + line + (tint("magenta", "▌") if typing else ""))
            else:
                body.append("")
        body += [""] * pad_v
        # Reserve every narration row so the block doesn't jump while it types.
        # align with the locked reticle, so narration stays put while it shrinks
        anchor = " " * max(0, (width - inner) // 2)
        narration = [anchor + line for line in narration]
        narration += [""] * (len(segment.narration) - len(narration))
        return _middle([*narration, *[""] * spacer, top, *body, bottom], height)

    def _ending(self, segment: Segment, local: float, width: int, height: int) -> str:
        ow = self.lore.overwatch
        if local >= segment.duration - 1.0:
            rows = self._banner_rows(tuple(ow.terminated.split()), width)
            return self._center(
                [tint("danger", text, "bold") for text, _ in rows],
                [size for _, size in rows],
                width,
                height,
            )
        typed = 1.0 if not self.motion else _clamp(local / COUNTDOWN_START)
        lines = list(segment.narration)
        total = sum(len(line) for line in lines)
        budget = round(total * typed)
        out: list[str] = []
        for number, line in enumerate(lines):
            shown = line[: max(0, budget)]
            budget -= len(line)
            if not shown:
                break
            if number == 0:
                out.append(tint("danger", "⚠ " + shown, "bold"))
            else:
                out.append(tint("text", shown, "bold"))
        if typed >= 1.0:
            out += ["", "  " + tint("cyan", self.profile.contact.email, "bold underline"), ""]
            seconds = max(0, int(local - COUNTDOWN_START) + 1) if self.motion else COUNTDOWN_FROM
            ticks = [f"{COUNTDOWN_FROM - n}…" for n in range(min(seconds, COUNTDOWN_FROM))]
            out.append(tint("yellow", "connection terminates in " + " ".join(ticks)))
            out += ["", tint("dim", ow.disclaimer)]
        # sized for the finished card so lines don't drift while they type in
        return _middle(out, height, rows=len(lines) + 7)


def _middle(lines: list[str], height: int, rows: int | None = None) -> str:
    """Vertically center ``lines`` (sized as ``rows`` if given, for a stable position)."""
    top = max(0, (height - (rows if rows is not None else len(lines))) // 2)
    return "\n".join([""] * top + lines)


def _mmss(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
