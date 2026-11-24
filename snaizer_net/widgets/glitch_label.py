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
        prefix: str = "",
        chance: float = 0.02,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.color = color
        self.prefix = prefix
        """Markup drawn before the text; never glitched."""
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
        return self.prefix + tint(self.color, self.text, "bold")

    def _glitched(self) -> str:
        chars = list(self.text)
        for index, char in enumerate(chars):
            if char != " " and self._rng.random() < 0.18:
                chars[index] = self._rng.choice(GLITCH_CHARS)
        split = self._rng.randint(0, len(chars))
        shift = " " * self._rng.randint(0, 2)
        left, right = "".join(chars[:split]), "".join(chars[split:])
        a, b = self._rng.sample(SPLIT_COLORS, 2)
        return f"{self.prefix}{shift}{tint(a, left, 'bold')}{tint(b, right, 'bold')}"

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
    """A block-font banner with a brief row-shift / color-split glitch.

    It picks the widest layout that fits its container: the lines as given,
    then one segment per line (``SNAIZER`` over ``//NET``), then letter-spaced
    text, then plain text, so it never overflows a phone screen.
    """

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
        self.layout_name = "block"
        self._frames_left = 0
        self._rng = random.Random()

    def on_mount(self) -> None:
        """Draw the banner and start the glitch timer."""
        self._redraw()
        self.set_interval(1 / ANIM_FPS, self._tick)

    def watch_compact(self) -> None:
        """Redraw when switching between full and compact font."""
        self._redraw()

    def glitch(self, frames: int = 5) -> None:
        """Glitch for a few frames (no-op when animations are disabled)."""
        if motion_enabled(self):
            self._frames_left = frames
            self.update(self._banner_markup(glitch=True))

    def _redraw(self) -> None:
        self.layout_name = self._pick_layout()
        self.update(self._banner_markup(glitch=False))

    def _available(self) -> int:
        """Width of the container we must fit in (0 before the first layout)."""
        parent = self.parent
        return parent.size.width if parent is not None and hasattr(parent, "size") else 0

    def _seg_width(self, text: str) -> int:
        return len(render_banner(text, self.compact)[0])

    def _block_lines(self, stacked: bool) -> list[list[tuple[str, str]]]:
        """Lines as given, or re-packed greedily so each fits the container."""
        if not stacked:
            return self.lines
        room = self._available() or 10_000
        packed: list[list[tuple[str, str]]] = []
        for line in self.lines:
            current: list[tuple[str, str]] = []
            used = 0
            for segment in line:
                width = self._seg_width(segment[0])
                if current and used + 1 + width > room:
                    packed.append(current)
                    current, used = [], 0
                used += width + (1 if current else 0)
                current.append(segment)
            packed.append(current)
        return packed

    def _block_width(self, stacked: bool) -> int:
        widths = [
            sum(self._seg_width(text) for text, _ in line) + len(line) - 1
            for line in self._block_lines(stacked)
        ]
        return max(widths, default=0)

    def _text_lines(self, spaced: bool) -> list[list[tuple[str, str]]]:
        sep = " " if spaced else ""
        return [[(sep.join(text), color) for text, color in line] for line in self.lines]

    def _pick_layout(self) -> str:
        width = self._available()
        if not width or self._block_width(stacked=False) <= width:
            return "block"
        if self._block_width(stacked=True) <= width:
            return "stacked"
        spaced = max(
            (sum(len(text) for text, _ in line) + len(line) - 1)
            for line in self._text_lines(spaced=True)
        )
        return "spaced" if spaced <= width else "plain"

    def _rows(self) -> list[list[tuple[str, str]]]:
        """Rendered rows as (text, color) segments, with a blank row between lines."""
        if self.layout_name in ("spaced", "plain"):
            text_rows: list[list[tuple[str, str]]] = []
            for line in self._text_lines(spaced=self.layout_name == "spaced"):
                row: list[tuple[str, str]] = []
                for index, part in enumerate(line):
                    if index:
                        row.append((" ", ""))
                    row.append(part)
                text_rows.append(row)
            return text_rows
        rows: list[list[tuple[str, str]]] = []
        for line_index, line in enumerate(self._block_lines(self.layout_name == "stacked")):
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
                out.append(
                    "".join(tint(color, seg, "bold") if color else seg for seg, color in segments)
                )
        return "\n".join(out)

    def _tick(self) -> None:
        if self._pick_layout() != self.layout_name:  # the container was resized
            self._redraw()
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
