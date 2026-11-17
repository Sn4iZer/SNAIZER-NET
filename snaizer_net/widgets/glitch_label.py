"""Glitching text: a one-line label and a multi-row block banner."""

import random
from collections.abc import Sequence

from textual.reactive import reactive
from textual.widgets import Static

from snaizer_net.assets.ascii import render_banner
from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

GLITCH_CHARS = "▓▒░#%&$@!/\\"
SPLIT_COLORS = ("cyan", "magenta")


class GlitchLabel(Static):
    """A label that occasionally glitches with a cyan/magenta color split."""

    DEFAULT_CSS = "GlitchLabel { height: 1; width: 1fr; }"

    def __init__(
        self,
        text: str,
        *,
        color: str = "cyan",
        chance: float = 0.02,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.color = color
        self.chance = chance
        self._frames_left = 0
        self._rng = random.Random()

    def on_mount(self) -> None:
        """Render the clean text and start the (cheap) glitch timer."""
        self.update(self._clean())
        self.set_interval(1 / ANIM_FPS, self._tick)

    def set_text(self, text: str, glitch: bool = True) -> None:
        """Change the label and optionally kick off a short glitch burst."""
        self.text = text
        self._frames_left = 0
        self.update(self._clean())
        if glitch:
            self.glitch()

    def glitch(self, frames: int = 4) -> None:
        """Glitch for a few frames (no-op when animations are disabled)."""
        if motion_enabled(self):
            self._frames_left = frames
            self.update(self._glitched())

    def _clean(self) -> str:
        return tint(self.color, self.text, "bold")

    def _glitched(self) -> str:
        chars = list(self.text)
        for index, char in enumerate(chars):
            if char != " " and self._rng.random() < 0.18:
                chars[index] = self._rng.choice(GLITCH_CHARS)
        split = self._rng.randint(0, len(chars))
        shift = " " * self._rng.randint(0, 2)
        left, right = "".join(chars[:split]), "".join(chars[split:])
        a, b = self._rng.sample(SPLIT_COLORS, 2)
        return f"{shift}{tint(a, left, 'bold')}{tint(b, right, 'bold')}"

    def _tick(self) -> None:
        if not motion_enabled(self) or not self.display:
            if self._frames_left:
                self._frames_left = 0
                self.update(self._clean())
            return
        if self._frames_left:
            self._frames_left -= 1
            self.update(self._glitched() if self._frames_left else self._clean())
        elif self._rng.random() < self.chance:
            self.glitch(self._rng.randint(2, 4))


BannerLine = Sequence[tuple[str, str]]
"""One banner line: a sequence of (text, color) segments."""


class GlitchBanner(Static):
    """A block-font banner with a brief row-shift / color-split glitch."""

    DEFAULT_CSS = "GlitchBanner { height: auto; width: auto; }"

    compact: reactive[bool] = reactive(False)

    def __init__(
        self,
        lines: Sequence[BannerLine],
        *,
        chance: float = 0.015,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.lines = [list(line) for line in lines]
        self.chance = chance
        self._frames_left = 0
        self._rng = random.Random()

    def on_mount(self) -> None:
        """Draw the banner and start the glitch timer."""
        self.update(self._banner_markup(glitch=False))
        self.set_interval(1 / ANIM_FPS, self._tick)

    def watch_compact(self) -> None:
        """Redraw when switching between full and compact font."""
        self.update(self._banner_markup(glitch=False))

    def glitch(self, frames: int = 5) -> None:
        """Glitch for a few frames (no-op when animations are disabled)."""
        if motion_enabled(self):
            self._frames_left = frames
            self.update(self._banner_markup(glitch=True))

    def _rows(self) -> list[list[tuple[str, str]]]:
        """Rendered rows as (text, color) segments, with a blank row between lines."""
        rows: list[list[tuple[str, str]]] = []
        for line_index, line in enumerate(self.lines):
            if line_index:
                rows.append([])
            rendered = [(render_banner(text, self.compact), color) for text, color in line]
            for row in range(len(rendered[0][0])):
                segments: list[tuple[str, str]] = []
                for seg_index, (glyph_rows, color) in enumerate(rendered):
                    if seg_index:
                        segments.append((" ", color))
                    segments.append((glyph_rows[row], color))
                rows.append(segments)
        return rows

    def _banner_markup(self, glitch: bool) -> str:
        rows = self._rows()
        broken = set()
        if glitch and rows:
            broken = set(self._rng.sample(range(len(rows)), k=min(2, len(rows))))
        out = []
        for index, segments in enumerate(rows):
            if index in broken:
                shift = self._rng.choice((1, 2))
                color = self._rng.choice(SPLIT_COLORS)
                text = "".join(seg for seg, _ in segments)
                noisy = "".join(
                    self._rng.choice("▓▒░") if ch != " " and self._rng.random() < 0.12 else ch
                    for ch in text
                )
                out.append(" " * shift + tint(color, noisy, "bold"))
            else:
                out.append("".join(tint(color, seg, "bold") for seg, color in segments))
        return "\n".join(out)

    def _tick(self) -> None:
        if not motion_enabled(self) or not self.display:
            if self._frames_left:
                self._frames_left = 0
                self.update(self._banner_markup(glitch=False))
            return
        if self._frames_left:
            self._frames_left -= 1
            self.update(self._banner_markup(glitch=bool(self._frames_left)))
        elif self._rng.random() < self.chance:
            self.glitch(self._rng.randint(2, 4))


LOGO_LINES: list[BannerLine] = [[("SNAIZER", "cyan"), ("//", "yellow"), ("NET", "magenta")]]
