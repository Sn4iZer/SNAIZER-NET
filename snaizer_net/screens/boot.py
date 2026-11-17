"""Screen 1: BIOS-style boot sequence (skippable with any key or click)."""

import time

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.content import Lore
from snaizer_net.markup import safe, tint
from snaizer_net.screens._app import snaizer_app
from snaizer_net.widgets.glitch_label import LOGO_LINES, GlitchBanner
from snaizer_net.widgets.motion import motion_enabled

LINE_INTERVAL = 0.33
STATUS_COLORS = {"OK": "green", "WARN": "yellow", "FAIL": "danger"}
BAR_WIDTH = 40
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class BootScreen(Screen[None]):
    """Streams fictional boot logs, glitches the logo, fills a progress bar."""

    def __init__(self, lore: Lore) -> None:
        super().__init__()
        self.lore = lore
        self.stamps: list[float] = []
        self.handed_over = False
        self.spin_frame = 0
        self._t0 = time.monotonic()

    @property
    def printed(self) -> int:
        """Number of boot lines shown so far."""
        return len(self.stamps)

    def compose(self) -> ComposeResult:
        """Logo, log and progress bar."""
        with Vertical(id="boot-wrap"):
            yield GlitchBanner(LOGO_LINES, chance=0.08, id="boot-logo")
            yield Static("", id="boot-log")
            yield Static("", id="boot-progress")
            yield Static(tint("dim", "press any key to skip"), id="boot-hint")

    def on_mount(self) -> None:
        """Start streaming lines, or print everything at once without motion."""
        self.query_one(GlitchBanner).compact = self.app.size.height < 34
        if motion_enabled(self):
            self.query_one(GlitchBanner).glitch(6)
            self._ticker = self.set_interval(LINE_INTERVAL, self._next_line)
            self._spinner = self.set_interval(1 / ANIM_FPS, self._spin)
        else:
            self.stamps = [0.0] * len(self.lore.boot_lines)
            self.set_timer(1.5, self.finish)
        self._render_log()

    def _next_line(self) -> None:
        if self.printed < len(self.lore.boot_lines):
            self.stamps.append(time.monotonic() - self._t0)
            self._render_log()
        else:
            self._ticker.stop()
            self._spinner.stop()
            self._render_log()
            self.query_one(GlitchBanner).glitch(4)  # final flicker before the gate
            self.set_timer(0.5, self.finish)

    def _spin(self) -> None:
        self.spin_frame += 1
        self._render_log()

    def _render_log(self) -> None:
        lines = []
        for line, stamp in zip(self.lore.boot_lines, self.stamps, strict=False):
            color = STATUS_COLORS.get(line.status, "cyan")
            lines.append(
                f"{tint('dim', f'[{stamp:10.6f}]')} "
                f"{tint('dim', '[')}{tint(color, f'{line.status:^4}', 'bold')}{tint('dim', ']')} "
                f"{safe(line.text)}"
            )
        if motion_enabled(self) and self.printed < len(self.lore.boot_lines):
            upcoming = self.lore.boot_lines[self.printed]
            spinner = SPINNER[self.spin_frame % len(SPINNER)]
            stamp = time.monotonic() - self._t0
            lines.append(
                f"{tint('dim', f'[{stamp:10.6f}]')} "
                f"{tint('dim', '[')}{tint('magenta', f' {spinner}  ', 'bold')}{tint('dim', ']')} "
                f"{tint('dim', upcoming.text)}"
            )
        self.query_one("#boot-log", Static).update("\n".join(lines))
        progress = self.printed / max(1, len(self.lore.boot_lines))
        filled = round(progress * BAR_WIDTH)
        self.query_one("#boot-progress", Static).update(
            f"{tint('magenta', 'LOADING', 'bold')} "
            f"{tint('cyan', '█' * filled)}{tint('dim', '░' * (BAR_WIDTH - filled))} "
            f"{tint('yellow', f'{progress:4.0%}')}"
        )

    def finish(self) -> None:
        """Hand over to the fake login (only once)."""
        if not self.handed_over:
            self.handed_over = True
            snaizer_app(self).show_login()

    def on_key(self, event: events.Key) -> None:
        """Any key skips the boot sequence."""
        event.stop()
        self.finish()

    def on_click(self) -> None:
        """A click skips too."""
        self.finish()
