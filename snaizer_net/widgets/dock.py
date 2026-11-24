"""Bottom navigation for phones: big tap targets instead of keyboard shortcuts."""

from collections.abc import Sequence
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Static

from snaizer_net.markup import tint
from snaizer_net.navigation import SectionSpec

DockAction = Literal["prev", "menu", "next"]


class DockButton(Static):
    """One third of the dock; a tap posts :class:`PocketDock.Pressed`."""

    def __init__(self, action: DockAction) -> None:
        super().__init__(id=f"dock-{action}", classes="dock-button")
        self.action = action

    def on_click(self) -> None:
        """Report the tap to the screen."""
        self.post_message(PocketDock.Pressed(self.action))


class PocketDock(Horizontal):
    """``‹ previous   ☰ menu   next ›``, labelled with the neighbouring sections."""

    class Pressed(Message):
        """A dock button was tapped."""

        def __init__(self, action: DockAction) -> None:
            super().__init__()
            self.action = action

    def __init__(self, sections: Sequence[SectionSpec], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.sections = list(sections)

    def compose(self) -> ComposeResult:
        """Previous, menu, next."""
        for action in ("prev", "menu", "next"):
            yield DockButton(action)

    def set_current(self, section_id: str) -> None:
        """Label prev/next with the sections they lead to (wrapping around)."""
        ids = [spec.id for spec in self.sections]
        index = ids.index(section_id) if section_id in ids else 0
        before = self.sections[(index - 1) % len(ids)]
        after = self.sections[(index + 1) % len(ids)]
        self.query_one("#dock-prev", Static).update(
            f"{tint('cyan', '‹', 'bold')} {tint('dim', before.title)}"
        )
        self.query_one("#dock-menu", Static).update(tint("cyan", "☰ menu", "bold"))
        self.query_one("#dock-next", Static).update(
            f"{tint('dim', after.title)} {tint('cyan', '›', 'bold')}"
        )
