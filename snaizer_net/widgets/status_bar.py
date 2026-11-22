"""Top HUD: fake CPU/NET readings, real uptime and clock, user badge."""

import random
import time
from datetime import datetime

from textual.widgets import Static

from snaizer_net.markup import safe, tint


class StatusBar(Static):
    """One-line status bar that drops low-priority items when narrow."""

    DEFAULT_CSS = "StatusBar { height: 1; width: 1fr; }"

    def __init__(self, user: str, admin: bool, mode: str, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.user = user
        self.admin = admin
        self.mode = mode
        self.cpu = 23
        self.net = 1.2
        self._rng = random.Random()
        self._started = time.monotonic()

    def on_mount(self) -> None:
        """Tick once per second."""
        self._tick()
        self.set_interval(1.0, self._tick)

    def on_resize(self) -> None:
        """Re-fit items to the new width."""
        self.update(self._compose_line())

    def _tick(self) -> None:
        self.cpu = max(3, min(97, self.cpu + self._rng.randint(-7, 7)))
        self.net = max(0.1, min(99.9, self.net + self._rng.uniform(-0.8, 0.8)))
        self.update(self._compose_line())

    def _compose_line(self) -> str:
        elapsed = int(time.monotonic() - self._started)
        hours, rest = divmod(elapsed, 3600)
        minutes, seconds = divmod(rest, 60)
        cpu_bar = "▮" * (self.cpu // 20) + "▯" * (5 - self.cpu // 20)
        cpu = f"{self.cpu:>2}% "
        net = f"{self.net:4.1f}MB/s"
        link = self.mode
        clock = datetime.now().strftime("%H:%M:%S")
        uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        # (plain text for width accounting, markup) in priority order.
        # Labels are dim lowercase so the values carry the weight.
        items: list[tuple[str, str]] = [
            ("▓▒░ SNAIZER//NET", tint("magenta", "▓▒░ SNAIZER//NET", "bold")),
            (f"user {self.user}", tint("dim", "user ") + tint("green", self.user, "bold")),
        ]
        if self.admin:
            items.append((" ADMIN ", "[reverse $neon-yellow bold] ADMIN [/]"))
        items += [
            (clock, tint("yellow", clock)),
            (f"up {uptime}", tint("dim", "up ") + safe(uptime)),
            (f"cpu {cpu}{cpu_bar}", tint("dim", "cpu ") + safe(cpu) + tint("cyan", cpu_bar)),
            (f"net {net}", tint("dim", "net ") + safe(net)),
            (f"link {link}", tint("dim", "link ") + safe(link)),
        ]  # fmt: skip
        return fit_items(items, self.size.width or 80)


def fit_items(items: list[tuple[str, str]], width: int) -> str:
    """Join ``(plain, markup)`` items with separators, dropping those that overflow."""
    chosen: list[str] = []
    used = 0
    for plain, markup in items:
        cost = len(plain) + (3 if chosen else 0)
        if used + cost > width:
            break
        chosen.append(markup)
        used += cost
    return tint("dim", " │ ").join(chosen)


GLOBAL_HINTS = [
    ("0-9", "jump"),
    ("/", "search"),
    ("↑↓ jk TAB", "move"),
    ("PgUp/PgDn", "scroll"),
    ("m", "rain"),
    ("?", "help"),
    ("q", "quit"),
]
CONTEXT_HINTS = {
    "projects": [("↑↓ jk", "pick"), ("ENTER", "open"), ("f", "filter"), ("0-9", "jump")],
    "terminal": [
        ("ESC", "leave terminal"),
        ("TAB", "complete"),
        ("↑↓", "history"),
        ("exit", "quit"),
    ],
    "contact": [("d", "decrypt phone")],
}


class KeyHints(Static):
    """Bottom key-hint footer that adapts to the current section and width."""

    DEFAULT_CSS = "KeyHints { height: 1; width: 1fr; }"

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.context = ""

    def set_context(self, section_id: str) -> None:
        """Show hints relevant to ``section_id``."""
        self.context = section_id
        self.update(self._line())

    def on_resize(self) -> None:
        """Re-fit to the new width."""
        self.update(self._line())

    def _line(self) -> str:
        hints = CONTEXT_HINTS.get(self.context, []) + GLOBAL_HINTS
        seen: set[str] = set()
        items = []
        for key, label in hints:
            if key in seen:
                continue
            seen.add(key)
            items.append((f"{key} {label}", f"{tint('cyan', key, 'bold')} {tint('dim', label)}"))
        return fit_items(items, self.size.width or 80)
