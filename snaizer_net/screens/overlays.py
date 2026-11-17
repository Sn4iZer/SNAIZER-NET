"""Modal overlays: help, matrix rain, and the "terminal too small" notice."""

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from snaizer_net.config import MIN_HEIGHT, MIN_WIDTH
from snaizer_net.markup import tint
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
            "",
        ]
        rows.append(tint("dim", "press ESC or ? to close"))
        with Vertical(id="help-box"):
            yield Static("\n".join(rows))

    def on_click(self) -> None:
        """Click anywhere to close."""
        self.dismiss()


class MatrixScreen(ModalScreen[None]):
    """Full-screen digital rain; any key or click returns."""

    def compose(self) -> ComposeResult:
        """Rain with a centered tagline."""
        yield MatrixRain(id="rain")
        with Center(id="rain-caption"):
            yield Static(
                tint("green", " WAKE UP, RUNNER ", "bold reverse")
                + tint("dim", "  any key to return"),
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
        self.query_one("#too-small", Static).update(
            f"{tint('danger', '▓ SIGNAL TOO WEAK ▓', 'bold')}\n\n"
            f"Enlarge your terminal to at least {minimum}\n"
            f"{tint('dim', f'current: {width}x{height}')}"
        )
