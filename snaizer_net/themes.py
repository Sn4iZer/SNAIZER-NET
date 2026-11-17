"""Color palettes exposed to ``theme.tcss`` as ``$neon-*`` CSS variables.

Every widget styles itself with these variables (in CSS or in markup such as
``[$neon-cyan]``), so switching theme recolors the whole UI live.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass

from textual.theme import Theme


@dataclass(frozen=True)
class Palette:
    """The nine colors a theme is made of."""

    bg: str
    panel: str
    cyan: str
    magenta: str
    yellow: str
    green: str
    danger: str
    dim: str
    text: str


PALETTES: dict[str, Palette] = {
    "neon-night": Palette(
        bg="#0a0a12",
        panel="#10101c",
        cyan="#00f0ff",
        magenta="#ff2bd6",
        yellow="#fcee09",
        green="#39ff14",
        danger="#ff3355",
        dim="#6b7a99",
        text="#d6e4ff",
    ),
    "synthwave": Palette(
        bg="#140a24",
        panel="#1e1036",
        cyan="#36f9f6",
        magenta="#ff7edb",
        yellow="#fede5d",
        green="#72f1b8",
        danger="#fe4450",
        dim="#8d7aa8",
        text="#f4eeff",
    ),
    "toxic-green": Palette(
        bg="#050a05",
        panel="#0b140b",
        cyan="#39ff14",
        magenta="#b6ff00",
        yellow="#e6ff3b",
        green="#39ff14",
        danger="#ff3b3b",
        dim="#4f7a4f",
        text="#c8ffc0",
    ),
    "red-alert": Palette(
        bg="#0f0505",
        panel="#1a0808",
        cyan="#ff3355",
        magenta="#ff8a00",
        yellow="#ffd000",
        green="#9dff6b",
        danger="#ff0040",
        dim="#8a5a5a",
        text="#ffe0e0",
    ),
    # Exact ANSI colors so 16-color terminals map them without dithering.
    "neon-16": Palette(
        bg="#000000",
        panel="#000000",
        cyan="#00ffff",
        magenta="#ff00ff",
        yellow="#ffff00",
        green="#00ff00",
        danger="#ff0000",
        dim="#808080",
        text="#ffffff",
    ),
}

DEFAULT_THEME = "neon-night"
LOW_COLOR_THEME = "neon-16"
USER_THEMES: tuple[str, ...] = ("neon-night", "synthwave", "toxic-green", "red-alert", "neon-16")

LOW_COLOR_TERMS = {
    "ansi",
    "cygwin",
    "linux",
    "rxvt",
    "screen",
    "vt100",
    "vt220",
    "xterm",
    "xterm-16color",
    "xterm-color",
}


def theme_variables(palette: Palette) -> dict[str, str]:
    """Map a palette to the ``neon-*`` CSS variables used by ``theme.tcss``."""
    return {f"neon-{key}": value for key, value in asdict(palette).items()}


def build_theme(name: str, palette: Palette) -> Theme:
    """Create a Textual theme from a palette."""
    return Theme(
        name=name,
        primary=palette.cyan,
        secondary=palette.magenta,
        accent=palette.magenta,
        warning=palette.yellow,
        error=palette.danger,
        success=palette.green,
        foreground=palette.text,
        background=palette.bg,
        surface=palette.panel,
        panel=palette.panel,
        dark=True,
        variables=theme_variables(palette),
    )


def all_themes() -> list[Theme]:
    """Every theme the app registers."""
    return [build_theme(name, palette) for name, palette in PALETTES.items()]


def is_low_color_terminal(environ: Mapping[str, str]) -> bool:
    """Guess whether the terminal only supports the basic 16 ANSI colors."""
    if environ.get("COLORTERM", "").lower() in {"truecolor", "24bit"}:
        return False
    term = environ.get("TERM", "").lower()
    if not term or "256" in term or "direct" in term or "truecolor" in term:
        return False
    return term in LOW_COLOR_TERMS or term == "dumb"
