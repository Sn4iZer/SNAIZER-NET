"""Command palette (``/`` or ``ctrl+p``): fuzzy-jump to sections, dossiers, filters, themes."""

from collections.abc import Callable
from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from snaizer_net.screens._app import snaizer_app
from snaizer_net.screens.main import MainScreen
from snaizer_net.sections.panes import filter_tags
from snaizer_net.themes import USER_THEMES

Entry = tuple[str, Callable[[], object], str]


class SnaizerCommands(Provider):
    """Every navigable thing in the HUD, as palette commands."""

    def entries(self) -> list[Entry]:
        """Commands available from the main screen (empty elsewhere)."""
        screen = self.screen
        if not isinstance(screen, MainScreen):
            return []
        app = snaizer_app(screen)
        profile = screen.profile
        entries: list[Entry] = [
            (f"Go to {spec.title}", partial(screen.show_section, spec.id), f"key {spec.key}")
            for spec in screen.sections
        ]
        entries += [
            (
                f"Open dossier: {p.title}",
                partial(screen.open_project, p.slug),
                f"{p.kind}, {p.year}",
            )
            for p in profile.projects
        ]
        entries.append(("Filter projects: ALL", partial(screen.filter_projects, None), "f"))
        entries += [
            (f"Filter projects: {tag}", partial(screen.filter_projects, tag), "f")
            for tag in filter_tags(profile.projects)
        ]
        entries += [
            (f"Theme: {name}", partial(app.set_neon_theme, name), "theme") for name in USER_THEMES
        ]
        entries += [
            ("Matrix rain", screen.action_matrix, "m"),
            ("Toggle animations", app.toggle_animations, "accessibility"),
            ("Help: keyboard reference", screen.action_help, "?"),
            ("Quit", app.exit, "q"),
        ]
        return entries

    async def discover(self) -> Hits:
        """Shown before anything is typed."""
        for text, command, help_text in self.entries():
            yield DiscoveryHit(text, command, help=help_text)

    async def search(self, query: str) -> Hits:
        """Fuzzy-match the query against every entry."""
        matcher = self.matcher(query)
        for text, command, help_text in self.entries():
            score = matcher.match(text)
            if score > 0:
                yield Hit(score, matcher.highlight(text), command, help=help_text)
