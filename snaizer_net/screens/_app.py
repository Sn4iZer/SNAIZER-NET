"""Typed access to the running :class:`~snaizer_net.app.SnaizerApp`."""

from typing import TYPE_CHECKING, cast

from textual.dom import DOMNode

if TYPE_CHECKING:
    from snaizer_net.app import SnaizerApp


def snaizer_app(node: DOMNode) -> "SnaizerApp":
    """The app instance, typed as SnaizerApp."""
    return cast("SnaizerApp", node.app)
