"""Animated neon progress bar for one skill."""

from textual.widget import Widget

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import safe, tint
from snaizer_net.widgets.motion import motion_enabled

FILL_SECONDS = 0.8
MAX_BAR = 60


class SkillBar(Widget):
    """``Python (OOP)   ━━━━━━━━━━━━━━╸─────  90%``, filling up when shown."""

    DEFAULT_CSS = "SkillBar { height: 1; width: 1fr; }"

    def __init__(
        self,
        title: str,
        level: int,
        *,
        label: str | None = None,
        title_width: int = 18,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self.title = title
        self.level = level
        self.label = label or f"{level:>3}%"
        self.title_width = title_width
        self.value = 0.0

    def on_show(self) -> None:
        """Replay the fill animation each time the section becomes visible."""
        if not motion_enabled(self):
            self.value = float(self.level)
            self.refresh()
            return
        self.value = 0.0
        increment = self.level / (FILL_SECONDS * ANIM_FPS)

        def advance() -> None:
            self.value = min(float(self.level), self.value + increment)
            if self.value >= self.level or not motion_enabled(self):
                self.value = float(self.level)
                timer.stop()
            self.refresh()

        timer = self.set_interval(1 / ANIM_FPS, advance)

    def render(self) -> str:
        """Compose title, bar and label to fit the current width."""
        title_width = min(self.title_width, max(8, self.size.width // 3))
        title = (
            self.title if len(self.title) <= title_width else self.title[: title_width - 1] + "…"
        )
        bar_width = max(4, min(MAX_BAR, self.size.width - title_width - len(self.label) - 2))
        full = min(bar_width, round(self.value / 100 * bar_width))
        head = "╸" if 0 < full < bar_width else ""
        body = max(0, full - len(head))
        empty = bar_width - body - len(head)
        return (
            f"{safe(title.ljust(title_width))} "
            f"{tint('cyan', '━' * body)}{tint('magenta', head, 'bold')}{tint('dim', '─' * empty)} "
            f"{tint('yellow', self.label, 'bold')}"
        )
