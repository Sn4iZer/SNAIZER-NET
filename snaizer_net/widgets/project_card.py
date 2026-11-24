"""The "classified dossier" card that shows one project."""

from textual.widgets import Static

from snaizer_net.content import Project
from snaizer_net.markup import safe, tint

COLLAPSED_BULLETS = 2


def dossier_stamp(project: Project, index: int, short: bool = False) -> str:
    """The classified stamp shown in the dossier frame's top edge (short on phones)."""
    if short:
        return f"▓ CLASSIFIED #{index:02d} // {project.year}"
    return f"▓▒░ CLASSIFIED // CASE FILE #{index:02d} // {project.year} ░▒▓"


def dossier_markup(project: Project, expanded: bool) -> str:
    """Markup for a project dossier; collapsed shows only the first bullets."""
    bullets = project.bullets if expanded else project.bullets[:COLLAPSED_BULLETS]
    hidden = len(project.bullets) - len(bullets)
    lines = [
        tint("cyan", project.title, "bold"),
        tint("dim", project.kind),
        "",
        safe(project.summary),
        "",
        *(f"{tint('cyan', '▸')} {safe(bullet)}" for bullet in bullets),
    ]
    if hidden:
        noun = "line" if hidden == 1 else "lines"
        lines.append(tint("danger", f"▓▓▓ {hidden} more {noun} redacted. Enter declassifies."))
    lines += [
        "",
        " ".join(f"[$neon-cyan on $neon-panel] {safe(tag)} [/]" for tag in project.tags),
    ]
    return "\n".join(lines)


class ProjectCard(Static):
    """Displays the selected project; Enter toggles the expanded view."""

    def __init__(self, project: Project, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.project = project
        self.index = 1
        self.expanded = False

    def on_mount(self) -> None:
        """Render the initial dossier."""
        self.show(self.project, self.index)

    def show(self, project: Project, index: int, expanded: bool = False) -> None:
        """Display ``project`` (1-based ``index``)."""
        self.project, self.index, self.expanded = project, index, expanded
        self.border_title = dossier_stamp(project, index, short=self.app.has_class("-pocket"))
        self.border_subtitle = "Enter collapses" if expanded else "Enter expands"
        self.update(dossier_markup(project, expanded))

    def on_resize(self) -> None:
        """Rotating a phone can switch between the long and short stamp."""
        self.border_title = dossier_stamp(
            self.project, self.index, short=self.app.has_class("-pocket")
        )

    def toggle(self) -> None:
        """Expand or collapse the current dossier."""
        self.show(self.project, self.index, not self.expanded)
