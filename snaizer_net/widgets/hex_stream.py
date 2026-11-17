"""Scrolling hex dump used for the "decrypting session" animation."""

import random
from collections.abc import Callable

from textual.widgets import Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

ROWS = 6
BYTES_PER_ROW = 12


class HexStream(Static):
    """Shows random hex rows and a progress line, then calls ``on_done``."""

    DEFAULT_CSS = "HexStream { height: auto; width: auto; }"

    def __init__(self, *, id: str | None = None, classes: str | None = None) -> None:
        super().__init__(id=id, classes=classes)
        self._rng = random.Random()
        self._address = self._rng.randrange(0x100000, 0xF00000)

    def run(self, duration: float, on_done: Callable[[], None]) -> None:
        """Animate for ``duration`` seconds (a single frame without motion)."""
        if not motion_enabled(self):
            self.update(self._frame(1.0))
            self.set_timer(0.3, on_done)
            return
        total = max(1, int(duration * ANIM_FPS))
        frame = 0

        def tick() -> None:
            nonlocal frame
            frame += 1
            self.update(self._frame(frame / total))
            if frame >= total:
                timer.stop()
                on_done()

        timer = self.set_interval(1 / ANIM_FPS, tick)

    def _frame(self, progress: float) -> str:
        rows = []
        for _ in range(ROWS):
            self._address += BYTES_PER_ROW
            cells = []
            for _ in range(BYTES_PER_ROW):
                byte = f"{self._rng.randrange(256):02X}"
                cells.append(tint("green", byte) if self._rng.random() < 0.15 else byte)
            rows.append(f"{tint('dim', f'0x{self._address:06X}')}  {' '.join(cells)}")
        width = 24
        filled = round(progress * width)
        bar = tint("cyan", "█" * filled) + tint("dim", "░" * (width - filled))
        rows.append("")
        rows.append(f"{tint('magenta', 'DECRYPTING SESSION KEY', 'bold')} {bar} {progress:4.0%}")
        return "\n".join(rows)
