"""Helpers for building Textual markup from untrusted or content-file text."""

ZERO_WIDTH_SPACE = "\u200b"


def safe(text: str) -> str:
    r"""Escape ``text`` so no part of it is interpreted as markup.

    Textual treats ``\\[`` as a literal bracket, so every ``[`` is escaped
    (this also neutralizes ``[$var]`` tags, which :func:`textual.markup.escape`
    leaves alone). A trailing backslash would escape whatever tag follows it,
    so it is fenced off with a zero-width space.
    """
    escaped = text.replace("[", "\\[")
    if escaped.endswith("\\"):
        escaped += ZERO_WIDTH_SPACE
    return escaped


def tint(color: str, text: str, style: str = "") -> str:
    """Wrap escaped ``text`` in a theme color, e.g. ``tint("cyan", "hi")``."""
    extra = f" {style}" if style else ""
    return f"[$neon-{color}{extra}]{safe(text)}[/]"
