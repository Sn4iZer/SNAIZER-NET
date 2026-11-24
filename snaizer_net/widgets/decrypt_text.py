"""A sealed value that decodes itself character by character on request."""

import random
from collections.abc import Callable

from textual.widgets import Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

NOISE = "▓▒░█#%&@$01ABCDEF"
SCRAMBLE_FRAMES = 4
"""Frames of noise before the first character locks in."""


def sealed_mask(length: int, rng: random.Random) -> str:
    """Block-noise placeholder of ``length`` cells."""
    return "".join(rng.choice("▓▒░") for _ in range(length))


def decode_markup(plain: str, locked: int, rng: random.Random) -> str:
    """One frame of the decode effect: ``locked`` characters solved, the rest noise."""
    if locked >= len(plain):
        return tint("green", plain, "bold")
    noise = "".join(" " if ch == " " else rng.choice(NOISE) for ch in plain[locked:])
    return tint("green", plain[:locked], "bold") + tint("magenta", noise)


class DecryptText(Static):
    """Shows block noise until :meth:`reveal` decodes ``reader()`` into place."""

    def __init__(
        self,
        reader: Callable[[], str],
        length: int,
        *,
        id: str | None = None,
        classes: str | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._reader = reader
        self._rng = random.Random(seed)
        self.length = length
        self.revealed = False
        self.decoding = False
        self.plain = ""

    def on_mount(self) -> None:
        """Draw the sealed state."""
        self.update(tint("dim", sealed_mask(self.length, self._rng)))

    def reveal(self, on_done: Callable[[], None] | None = None) -> None:
        """Decode the value; locks one character per frame after a short scramble."""
        if self.revealed or self.decoding:
            return
        self.plain = self._reader()
        if not motion_enabled(self):
            self._finish(on_done)
            return
        self.decoding = True
        frame = 0

        def tick() -> None:
            nonlocal frame
            frame += 1
            locked = max(0, frame - SCRAMBLE_FRAMES)
            if locked >= len(self.plain):
                timer.stop()
                self._finish(on_done)
                return
            self.update(decode_markup(self.plain, locked, self._rng))

        timer = self.set_interval(1 / ANIM_FPS, tick)

    def _finish(self, on_done: Callable[[], None] | None) -> None:
        self.decoding = False
        self.revealed = True
        self.update(tint("green", self.plain, "bold"))
        if on_done is not None:
            on_done()
