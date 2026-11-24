"""A neon scanline that sweeps down the content pane on section changes."""

from textual.widget import Widget

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

SWEEP_FRAMES = 7


class ScanLine(Widget):
    """Absolutely positioned 1-row bar, hidden except while sweeping."""

    DEFAULT_CSS = """
    ScanLine {
        position: absolute;
        width: 100%;
        height: 1;
        display: none;
    }
    """

    def __init__(self, *, color: str = "cyan", id: str | None = None) -> None:
        super().__init__(id=id)
        self.color = color
        self.frame = 0
        self._sweeping = False

    def sweep(self) -> None:
        """Run one top-to-bottom sweep (ignored when animations are off)."""
        if not motion_enabled(self) or self._sweeping or self.parent is None:
            return
        self._sweeping = True
        self.frame = 0
        self.display = True
        height = max(1, self.parent.size.height)

        def tick() -> None:
            self.frame += 1
            self.styles.offset = (0, round(self.frame / SWEEP_FRAMES * (height - 1)))
            self.refresh()
            if self.frame >= SWEEP_FRAMES:
                timer.stop()
                self.display = False
                self._sweeping = False

        self.styles.offset = (0, 0)
        timer = self.set_interval(1 / ANIM_FPS, tick)

    def render(self) -> str:
        """A bright bar with fading edges."""
        width = max(0, self.size.width - 6)
        return tint("dim", "░▒▓") + tint(self.color, "▀" * width, "bold") + tint("dim", "▓▒░")
