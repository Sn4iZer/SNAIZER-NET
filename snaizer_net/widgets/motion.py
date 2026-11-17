"""Shared helper so every animated widget respects ``--no-anim``."""

from textual.dom import DOMNode


def motion_enabled(node: DOMNode) -> bool:
    """True if animations are allowed (flag set on the app, default on)."""
    return bool(getattr(node.app, "motion_enabled", True))
