"""Ledger rows: a right-aligned date column, a vertical rule, then the entry.

Dates are the information that orders a CV, so they get their own column
(yellow = time, everywhere in the app) instead of a border title on a card.
"""

from collections.abc import Sequence

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from snaizer_net.markup import safe, tint

DATE_COLUMN = 12
"""Longest date shown on one line; longer ranges break after the dash."""


def stack_date(when: str) -> str:
    """``Nov 2024–Apr 2025`` -> ``Nov 2024–`` / ``Apr 2025`` so dates never split mid-word."""
    if len(when) <= DATE_COLUMN or "–" not in when:
        return when
    start, end = when.split("–", 1)
    return f"{start}–\n{end}"


class LedgerEntry(Horizontal):
    """One dated entry. Wrapped body lines stay aligned to the content column."""

    def __init__(
        self,
        when: str,
        title: str,
        where: str,
        bullets: Sequence[str] = (),
        *,
        classes: str | None = None,
    ) -> None:
        super().__init__(classes=f"ledger {classes or ''}".strip())
        self.when = when
        self.title = title
        self.where = where
        self.bullets = tuple(bullets)

    def compose(self) -> ComposeResult:
        """Date column and body."""
        yield Static(tint("yellow", stack_date(self.when)), classes="ledger-when")
        lines = [tint("text", self.title, "bold"), tint("dim", self.where)]
        if self.bullets:
            lines.append("")
            lines += [f"{tint('cyan', '▸')} {safe(bullet)}" for bullet in self.bullets]
        yield Static("\n".join(lines), classes="ledger-body")
