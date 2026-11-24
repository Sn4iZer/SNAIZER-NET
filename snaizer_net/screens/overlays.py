"""Modal overlays: help, matrix rain, and the "terminal too small" notice."""

from collections.abc import Sequence

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from snaizer_net.config import MIN_HEIGHT, MIN_WIDTH
from snaizer_net.markup import tint
from snaizer_net.navigation import SectionSpec
from snaizer_net.widgets.matrix_rain import MatrixRain

HELP_ROWS = [
    ("0-9", "jump to a section (0 = BLACK-ICE, admins only)"),
    ("/ or ctrl+p", "command palette: search sections, dossiers, themes"),
    ("↑ ↓ / j k", "previous / next section"),
    ("TAB / shift+TAB", "next / previous section"),
    ("mouse", "click the navigation, buttons and list items"),
    ("ENTER", "expand / collapse a project dossier"),
    ("f / F", "cycle project tag filters"),
    ("PgUp / PgDn", "scroll the current section"),
    ("ESC", "leave the TERMINAL prompt"),
    ("m", "matrix rain mode"),
    ("?", "toggle this help"),
    ("q / ctrl+c", "quit"),
]


class HelpScreen(ModalScreen[None]):
    """Key reference."""

    BINDINGS = [
        Binding("escape,question_mark,q", "dismiss", "close", show=False),
    ]

    def compose(self) -> ComposeResult:
        """A framed table of keys."""
        width = max(len(key) for key, _ in HELP_ROWS)
        rows = [tint("magenta", "▓▒░ OPERATOR MANUAL ░▒▓", "bold"), ""]
        rows += [
            f"{tint('cyan', key.ljust(width), 'bold')}  {tint('text', what)}"
            for key, what in HELP_ROWS
        ]
        rows += [
            "",
            tint("dim", "TERMINAL: try help, neofetch, timeline, grep python, open 1, hack"),
            tint("dim", "On a phone: swipe to scroll, use the bar at the bottom to move."),
            "",
        ]
        rows.append(tint("dim", "press ESC or ? to close, or tap anywhere"))
        with Vertical(id="help-box"):
            yield Static("\n".join(rows))

    def on_click(self) -> None:
        """Click anywhere to close."""
        self.dismiss()


MenuChoice = str
"""A section id, or one of the ``action:*`` entries below."""

MENU_ACTIONS: tuple[tuple[str, str], ...] = (
    ("action:search", "search"),
    ("action:matrix", "matrix"),
    ("action:help", "help"),
    ("action:quit", "quit"),
)


class MenuItem(Vertical):
    """A large tappable row in the phone menu: a title and an optional note under it."""

    def __init__(
        self, choice: MenuChoice, title: str, note: str = "", *, classes: str = "menu-item"
    ) -> None:
        super().__init__(classes=classes)
        self.choice = choice
        self.title_markup = title
        self.note = note

    def compose(self) -> ComposeResult:
        """Title, then the note indented under it (wraps cleanly)."""
        yield Static(self.title_markup, classes="menu-item-title")
        if self.note:
            yield Static(tint("dim", self.note), classes="menu-item-note")

    def on_click(self) -> None:
        """Pick this entry (clicks on the title or note bubble up here)."""
        self.screen.dismiss(self.choice)


class MenuScreen(ModalScreen[MenuChoice | None]):
    """Full-screen section list for phones (opened from the dock)."""

    BINDINGS = [Binding("escape,q", "dismiss", "close", show=False)]

    def __init__(self, sections: Sequence[SectionSpec], current: str, hostname: str) -> None:
        super().__init__()
        self.sections = list(sections)
        self.current = current
        self.hostname = hostname

    def compose(self) -> ComposeResult:
        """Node name, quick actions, then one row per section."""
        with VerticalScroll(id="menu-box"):
            with Horizontal(id="menu-head"):
                yield Static(tint("magenta", "◢◤ " + self.hostname, "bold"), id="menu-title")
                yield MenuItem(
                    "action:close", tint("cyan", "✕ close", "bold"), classes="menu-close"
                )
            with Horizontal(id="menu-actions"):  # first, so they never scroll out of view
                for choice, label in MENU_ACTIONS:
                    yield MenuItem(choice, tint("cyan", label, "bold"), classes="menu-action")
            for spec in self.sections:
                item = MenuItem(
                    spec.id,
                    f"{tint('yellow', spec.key)}  {tint('text', spec.title, 'bold')}",
                    spec.blurb,
                )
                item.set_class(spec.id == self.current, "-active")
                item.set_class(spec.admin_only, "-admin")
                yield item

    def action_dismiss(self, result: MenuChoice | None = None) -> None:
        """Close without choosing."""
        self.dismiss(None)


class MatrixScreen(ModalScreen[None]):
    """Full-screen digital rain; any key or click returns."""

    def compose(self) -> ComposeResult:
        """Rain with a centered tagline."""
        yield MatrixRain(id="rain")
        with Center(id="rain-caption"):
            yield Static(
                tint("green", " WAKE UP, RUNNER ", "bold reverse")
                + tint("dim", "  any key or tap to return"),
            )

    def on_key(self, event: events.Key) -> None:
        """Any key leaves the rain."""
        event.stop()
        self.dismiss()

    def on_click(self) -> None:
        """A click leaves too."""
        self.dismiss()


class TooSmallScreen(ModalScreen[None]):
    """Shown while the terminal is smaller than the supported minimum."""

    def compose(self) -> ComposeResult:
        """A short, friendly message."""
        yield Static("", id="too-small")

    def on_mount(self) -> None:
        """Show the current size."""
        self.refresh_message(*self.app.size)

    def on_resize(self, event: events.Resize) -> None:
        """Keep the size readout current."""
        self.refresh_message(*event.size)

    def refresh_message(self, width: int, height: int) -> None:
        """Render the message for the given terminal size."""
        minimum = tint("cyan", f"{MIN_WIDTH}x{MIN_HEIGHT}", "bold")
        # short lines: this notice must fit the very screens that trigger it
        self.query_one("#too-small", Static).update(
            f"{tint('danger', '▓ SIGNAL TOO WEAK ▓', 'bold')}\n\n"
            f"Enlarge to at least\n{minimum} cells\n"
            f"{tint('dim', f'now {width}x{height}')}"
        )
