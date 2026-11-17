"""Digital rain, rendered as a Rich ``Text`` for speed."""

import random

from rich.style import Style
from rich.text import Text
from textual.widget import Widget

from snaizer_net.config import ANIM_FPS
from snaizer_net.themes import DEFAULT_THEME, PALETTES
from snaizer_net.widgets.motion import motion_enabled

GLYPHS = "0123456789ABCDEFｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉ$#*+=<>|"
TRAIL = 10


class MatrixRain(Widget):
    """Columns of falling glyphs that fill the widget."""

    DEFAULT_CSS = "MatrixRain { width: 1fr; height: 1fr; }"

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rng = random.Random()
        self._heads: list[float] = []
        self._speeds: list[float] = []
        self._grid: list[list[str]] = []

    def on_mount(self) -> None:
        """Start falling."""
        self.set_interval(1 / ANIM_FPS, self._tick)

    def on_resize(self) -> None:
        """Rebuild the columns for the new size."""
        width, height = self.size.width, max(1, self.size.height)
        self._heads = [self._rng.uniform(-height, height) for _ in range(width)]
        self._speeds = [self._rng.uniform(0.3, 1.0) for _ in range(width)]
        self._grid = [[self._rng.choice(GLYPHS) for _ in range(width)] for _ in range(height)]

    def _tick(self) -> None:
        if not motion_enabled(self) or not self._grid:
            return
        height = len(self._grid)
        for column, speed in enumerate(self._speeds):
            self._heads[column] += speed
            if self._heads[column] - TRAIL > height:
                self._heads[column] = self._rng.uniform(-height / 2, 0)
                self._speeds[column] = self._rng.uniform(0.3, 1.0)
        for _ in range(max(1, len(self._speeds) // 4)):
            row = self._rng.randrange(height)
            column = self._rng.randrange(len(self._speeds))
            self._grid[row][column] = self._rng.choice(GLYPHS)
        self.refresh()

    def render(self) -> Text:
        """Draw the current frame."""
        palette = PALETTES.get(self.app.theme, PALETTES[DEFAULT_THEME])
        head = Style(color=palette.text, bold=True)
        near = Style(color=palette.green)
        far = Style(color=palette.dim)
        text = Text(no_wrap=True, overflow="crop")
        for row_index, row in enumerate(self._grid):
            if row_index:
                text.append("\n")
            for column, glyph in enumerate(row):
                distance = self._heads[column] - row_index
                if 0 <= distance < 1:
                    text.append(glyph, head)
                elif 1 <= distance < TRAIL / 2:
                    text.append(glyph, near)
                elif TRAIL / 2 <= distance < TRAIL:
                    text.append(glyph, far)
                else:
                    text.append(" ")
        return text
