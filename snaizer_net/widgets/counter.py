"""A headline stat whose number counts up when it appears."""

import re

from textual.widgets import Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

NUMBER = re.compile(r"^(?P<prefix>\D*)(?P<number>\d[\d,]*(?:\.\d+)?)(?P<suffix>.*)$")
COUNT_SECONDS = 0.9


def format_partial(value: str, fraction: float) -> str:
    """``value`` with its number scaled by ``fraction``, keeping prefix/suffix/format.

    >>> format_partial("50,000+", 0.5)
    '25,000+'
    """
    match = NUMBER.match(value)
    if not match:
        return value
    raw = match["number"]
    target = float(raw.replace(",", ""))
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    current = target * max(0.0, min(1.0, fraction))
    number = f"{current:,.{decimals}f}" if "," in raw else f"{current:.{decimals}f}"
    return f"{match['prefix']}{number}{match['suffix']}"


class CounterStat(Static):
    """Inline stat ("5 projects"); the number counts up from zero on show."""

    def __init__(self, value: str, label: str, *, classes: str | None = None) -> None:
        super().__init__(classes=classes)
        self.value = value
        self.label = label

    def on_mount(self) -> None:
        """Render the final value until the animation starts."""
        self._draw(1.0)

    def on_show(self) -> None:
        """Count up each time the profile is displayed."""
        if not motion_enabled(self) or not NUMBER.match(self.value):
            self._draw(1.0)
            return
        frames = max(1, int(COUNT_SECONDS * ANIM_FPS))
        frame = 0

        def tick() -> None:
            nonlocal frame
            frame += 1
            # ease-out so the number decelerates as it lands
            progress = frame / frames
            self._draw(1 - (1 - progress) ** 3)
            if frame >= frames:
                timer.stop()

        self._draw(0.0)
        timer = self.set_interval(1 / ANIM_FPS, tick)

    def _draw(self, fraction: float) -> None:
        number = tint("cyan", format_partial(self.value, fraction), "bold")
        self.update(f"{number} {tint('dim', self.label)}")
