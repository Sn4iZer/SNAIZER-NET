"""Section navigation: a sidebar for wide terminals, a tab strip for narrow ones."""

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Static

from snaizer_net.markup import safe
from snaizer_net.navigation import SectionSpec


class NavItem(Static):
    """A clickable navigation entry."""

    class Selected(Message):
        """Posted when the item is clicked."""

        def __init__(self, section_id: str) -> None:
            super().__init__()
            self.section_id = section_id

    def __init__(self, spec: SectionSpec, compact: bool) -> None:
        label = f"{spec.key}:{spec.short}" if compact else f"[{spec.key}] {spec.title}"
        super().__init__(safe(label), classes="nav-item")
        self.spec = spec
        if spec.admin_only:
            self.add_class("-admin")

    def on_click(self) -> None:
        """Ask the screen to switch to this section."""
        self.post_message(self.Selected(self.spec.id))


def _mark_active(items: Sequence[NavItem], section_id: str) -> None:
    for item in items:
        item.set_class(item.spec.id == section_id, "-active")


class Sidebar(Vertical):
    """Vertical navigation menu."""

    def __init__(self, sections: Sequence[SectionSpec], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.sections = sections

    def compose(self) -> ComposeResult:
        """Header, one item per section, then a footer note."""
        yield Static("░▒▓ NAV ▓▒░", classes="nav-header")
        for spec in self.sections:
            yield NavItem(spec, compact=False)
        yield Static("", classes="nav-spacer")
        yield Static("/  search\nm  matrix\n?  help\nq  quit", classes="nav-footer")

    def set_active(self, section_id: str) -> None:
        """Highlight the current section."""
        _mark_active(list(self.query(NavItem)), section_id)


class TabStrip(Horizontal):
    """Horizontal navigation used when the terminal is narrow."""

    def __init__(self, sections: Sequence[SectionSpec], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.sections = sections

    def compose(self) -> ComposeResult:
        """One compact item per section."""
        for spec in self.sections:
            yield NavItem(spec, compact=True)

    def set_active(self, section_id: str) -> None:
        """Highlight the current section."""
        _mark_active(list(self.query(NavItem)), section_id)
