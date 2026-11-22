"""Text that types itself out, with a block cursor."""

from textual.widgets import Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import safe, tint
from snaizer_net.widgets.motion import motion_enabled


class Typewriter(Static):
    """Reveal ``text`` progressively the first time the widget is shown."""

    def __init__(
        self,
        text: str,
        *,
        chars_per_second: int = 90,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.text = text
        self.step = max(1, chars_per_second // ANIM_FPS)
        self.shown = 0
        self._started = False

    @property
    def done(self) -> bool:
        """True once the whole text is visible."""
        return self.shown >= len(self.text)

    def on_mount(self) -> None:
        """Draw the cursor alone until typing starts."""
        self._draw()

    def on_show(self) -> None:
        """Start typing on first display (instantly when animations are off)."""
        if self._started:
            return
        self._started = True
        if not motion_enabled(self):
            self.shown = len(self.text)
            # Show fires mid-layout; drawing now would keep the 1-line height.
            self.call_after_refresh(self._draw)
            return

        def advance() -> None:
            self.shown = min(len(self.text), self.shown + self.step)
            if self.done or not motion_enabled(self):
                self.shown = len(self.text)
                timer.stop()
            self._draw()

        timer = self.set_interval(1 / ANIM_FPS, advance)

    def _draw(self) -> None:
        self.update(safe(self.text[: self.shown]) + tint("magenta", "▌"))
