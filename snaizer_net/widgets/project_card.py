"""The "classified dossier" card that shows one project."""

from textual.widgets import Static

from snaizer_net.content import Project
from snaizer_net.markup import safe, tint

COLLAPSED_BULLETS = 2


def dossier_markup(project: Project, index: int, expanded: bool) -> str:
    """Markup for a project dossier; collapsed shows only the first bullets."""
    bullets = project.bullets if expanded else project.bullets[:COLLAPSED_BULLETS]
    hidden = len(project.bullets) - len(bullets)
    lines = [
        tint("danger", f"▓▒░ CLASSIFIED // CASE FILE #{index:02d} // {project.year} ░▒▓", "bold"),
        "",
        tint("cyan", project.title.upper(), "bold"),
        f"{tint('magenta', project.kind)}  {tint('dim', '·')}  {tint('yellow', str(project.year))}",
        tint("dim", "─" * 40),
        safe(project.summary),
        "",
        *(f"{tint('green', '▸')} {safe(bullet)}" for bullet in bullets),
    ]
    if hidden:
        lines.append(tint("dim", f"  … {hidden} more line(s) redacted. [ENTER] declassify"))
    lines += [
        "",
        tint("dim", "TAGS ")
        + " ".join(f"[$neon-bg on $neon-cyan] {safe(tag)} [/]" for tag in project.tags),
        "",
        tint("dim", "[ENTER] collapse dossier" if expanded else "[ENTER] expand dossier"),
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
        self.border_title = f"DOSSIER {index:02d}"
        self.update(dossier_markup(project, index, expanded))

    def toggle(self) -> None:
        """Expand or collapse the current dossier."""
        self.show(self.project, self.index, not self.expanded)
