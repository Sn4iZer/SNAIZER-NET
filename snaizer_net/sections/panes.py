"""Section widgets. Every fact comes from :class:`~snaizer_net.content.Profile`."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, ListItem, ListView, Static

from snaizer_net.assets.ascii import AVATAR, SKULL, TROPHY
from snaizer_net.config import ANIM_FPS
from snaizer_net.content import Lore, Profile, Project
from snaizer_net.markup import safe, tint
from snaizer_net.shell.commands import FakeShell
from snaizer_net.timeline import KIND_COLOR, KIND_GLYPH, build_timeline
from snaizer_net.widgets.counter import CounterStat
from snaizer_net.widgets.fake_shell import FakeShellWidget
from snaizer_net.widgets.motion import motion_enabled
from snaizer_net.widgets.project_card import ProjectCard
from snaizer_net.widgets.sensor_panel import SensorPanel
from snaizer_net.widgets.skill_bar import SkillBar
from snaizer_net.widgets.typewriter import Typewriter


class Section(VerticalScroll, can_focus=False):
    """Scrollable pane (mouse wheel / PgUp / PgDn); never steals arrow keys."""

    DEFAULT_CLASSES = "section"


class ProfileSection(Section):
    """Identity, typewriter bio and headline stats."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """Avatar + identity block, then stat boxes."""
        ident = self.profile.identity
        with Horizontal(id="profile-top"):
            yield Static("\n".join(AVATAR), classes="avatar")
            with Vertical(id="profile-ident"):
                yield Static(
                    f"{tint('cyan', ident.name.upper(), 'bold')}  "
                    f"{tint('magenta', '// ' + ident.handle, 'bold')}",
                    classes="profile-name",
                )
                yield Static(
                    f"{tint('yellow', ident.title)} {tint('dim', '·')} {safe(ident.location)}",
                    classes="profile-title",
                )
                yield Typewriter(ident.bio, id="bio")
        stats = [
            ("AWARDS", str(len(self.profile.awards))),
            ("PROJECTS", str(len(self.profile.projects))),
            *((item.label, item.value) for item in self.profile.highlights),
        ]
        with Horizontal(id="profile-stats"):
            for label, value in stats:
                yield CounterStat(value, label, classes="stat-box")
        yield SensorPanel(id="sensor-panel")


class TimelineSection(Section):
    """Education, experience, projects and awards on one animated time axis."""

    REVEAL_EVERY = 2
    """Frames between two entries appearing."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.entries = build_timeline(profile)
        self.revealed = len(self.entries)

    def compose(self) -> ComposeResult:
        """Legend and the timeline body."""
        legend = "   ".join(
            f"{tint(KIND_COLOR[kind], KIND_GLYPH[kind])} {tint('dim', kind.upper())}"
            for kind in KIND_COLOR
        )
        yield Static(legend, classes="caption")
        yield Static("", id="timeline-body")

    def on_show(self) -> None:
        """Replay the reveal each time the section opens."""
        if not motion_enabled(self):
            self.revealed = len(self.entries)
            self._draw()
            return
        self.revealed = 0
        frame = 0

        def tick() -> None:
            nonlocal frame
            frame += 1
            if frame % self.REVEAL_EVERY == 0:
                self.revealed += 1
                self._draw()
            if self.revealed >= len(self.entries):
                timer.stop()

        self._draw()
        timer = self.set_interval(1 / ANIM_FPS, tick)

    def _draw(self) -> None:
        width = max((len(entry.when) for entry in self.entries), default=4)
        lines: list[str] = []
        for index, entry in enumerate(self.entries[: self.revealed]):
            color = KIND_COLOR[entry.kind]
            node = tint(color, f"─{KIND_GLYPH[entry.kind]}─")
            lines.append(
                f"{tint('yellow', entry.when.rjust(width))} {node} "
                f"{tint(color, entry.title, 'bold')}"
            )
            last = index == len(self.entries) - 1
            lines.append(
                f"{' ' * width}  {tint('dim', ' ' if last else '│')}   "
                f"{tint('dim', entry.detail + ' · ' + entry.kind)}"
            )
        self.query_one("#timeline-body", Static).update("\n".join(lines))


class EducationSection(Section):
    """Degrees as a timeline of cards."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """One card per degree."""
        for edu in self.profile.education:
            card = Static(
                f"{tint('cyan', edu.degree, 'bold')}\n"
                f"{tint('magenta', '◆')} {safe(edu.institution)} {tint('dim', '·')} "
                f"{safe(edu.location)}",
                classes="card",
            )
            card.border_title = edu.period
            yield card


class SkillsSection(Section):
    """Neon skill bars per category, plus spoken languages."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """One panel per category."""
        yield Static(
            tint("dim", "bars show relative proficiency (stylized, not a certification)"),
            classes="caption",
        )
        for category in self.profile.skills:
            panel = Vertical(
                *(SkillBar(skill.name, skill.level) for skill in category.skills),
                classes="panel",
            )
            panel.border_title = category.name.upper()
            yield panel
        spoken = Vertical(
            *(SkillBar(lang.name, lang.bar, label=lang.level) for lang in self.profile.languages),
            classes="panel",
        )
        spoken.border_title = "SPOKEN"
        yield spoken


class ProjectList(ListView):
    """Project picker with vim keys."""

    BINDINGS = [
        Binding("j", "cursor_down", "down", show=False),
        Binding("k", "cursor_up", "up", show=False),
    ]


def filter_tags(projects: tuple[Project, ...]) -> list[str]:
    """Tags shared by at least two projects, most common first."""
    counts: dict[str, int] = {}
    for project in projects:
        for tag in project.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return sorted((tag for tag, n in counts.items() if n >= 2), key=lambda t: (-counts[t], t))


class ProjectsSection(Horizontal):
    """Project list (filterable by tag) on the left, dossier on the right."""

    DEFAULT_CLASSES = "section"
    BINDINGS = [
        Binding("f", "cycle_filter(1)", "filter", show=False),
        Binding("F", "cycle_filter(-1)", "previous filter", show=False),
    ]

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile
        self.filters: list[str | None] = [None, *filter_tags(profile.projects)]
        self.active_filter: str | None = None
        self.shown_projects: list[Project] = list(profile.projects)

    def number_of(self, project: Project) -> int:
        """Stable 1-based dossier number, independent of the filter."""
        return self.profile.projects.index(project) + 1

    def _item(self, project: Project) -> ListItem:
        number = self.number_of(project)
        return ListItem(
            Label(f"{tint('yellow', f'{number:02d}')} {safe(project.title)}"),
            classes="project-item",
        )

    def compose(self) -> ComposeResult:
        """List and card."""
        project_list = ProjectList(*(self._item(p) for p in self.shown_projects), id="project-list")
        yield project_list
        with VerticalScroll(id="dossier-scroll", can_focus=False):
            yield ProjectCard(self.profile.projects[0], id="dossier")

    def on_mount(self) -> None:
        """Label the list."""
        self._update_title()

    def _update_title(self) -> None:
        label = self.active_filter or "ALL"
        self.query_one(ProjectList).border_title = (
            f"MISSIONS · {label} ({len(self.shown_projects)})"
        )
        self.query_one(ProjectList).border_subtitle = "f: filter"

    async def set_filter(self, tag: str | None, select: Project | None = None) -> None:
        """Show only projects tagged ``tag`` (``None`` = all), optionally selecting one."""
        self.active_filter = tag
        self.shown_projects = [p for p in self.profile.projects if tag is None or tag in p.tags]
        project_list = self.query_one(ProjectList)
        await project_list.clear()
        await project_list.extend(self._item(p) for p in self.shown_projects)
        self._update_title()
        target = select if select in self.shown_projects else self.shown_projects[0]
        project_list.index = self.shown_projects.index(target)
        self.query_one(ProjectCard).show(
            target, self.number_of(target), expanded=select is not None
        )

    async def action_cycle_filter(self, delta: int) -> None:
        """Step through the tag filters."""
        index = (self.filters.index(self.active_filter) + delta) % len(self.filters)
        await self.set_filter(self.filters[index])

    async def open_project(self, slug: str) -> None:
        """Select a project by slug and show its expanded dossier."""
        project = next((p for p in self.profile.projects if p.slug == slug), None)
        if project is None:
            return
        tag = self.active_filter if project in self.shown_projects else None
        await self.set_filter(tag, select=project)
        self.focus_list()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Show the highlighted project collapsed."""
        index = event.list_view.index
        card = self.query_one(ProjectCard)
        if index is not None and index < len(self.shown_projects):
            project = self.shown_projects[index]
            if project is not card.project or not card.expanded:
                card.show(project, self.number_of(project))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Enter (or click) expands / collapses the dossier."""
        self.query_one(ProjectCard).toggle()

    def focus_list(self) -> None:
        """Give keyboard focus to the project list."""
        self.query_one(ProjectList).focus()


class AwardsSection(Section):
    """Trophy art plus one card per award."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """Trophy and cards side by side."""
        with Horizontal(id="awards-row"):
            yield Static("\n".join(TROPHY), classes="trophy")
            with Vertical(id="awards-cards"):
                for award in self.profile.awards:
                    card = Static(
                        f"{tint('yellow', '★ ' + award.place.upper(), 'bold')}\n"
                        f"{tint('cyan', award.title, 'bold')}\n"
                        f"{tint('magenta', award.organizer)} {tint('dim', '·')} "
                        f"{tint('yellow', str(award.year))}\n"
                        f"{safe(award.description)}",
                        classes="card",
                    )
                    card.border_title = str(award.year)
                    yield card


class ExperienceSection(Section):
    """Work and entrepreneurship entries."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """One card per entry."""
        for exp in self.profile.experience:
            bullets = "\n".join(f"{tint('green', '▸')} {safe(bullet)}" for bullet in exp.bullets)
            card = Static(
                f"{tint('cyan', exp.title, 'bold')} {tint('dim', '@')} "
                f"{tint('magenta', exp.organization)}\n\n{bullets}",
                classes="card",
            )
            card.border_title = exp.period
            yield card


class ContactSection(Section):
    """Contact channels; link buttons only in the web build."""

    def __init__(self, profile: Profile, web: bool, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile
        self.web = web

    def compose(self) -> ComposeResult:
        """Contact lines and actions."""
        contact = self.profile.contact
        link = "bold underline"
        card = Static(
            "\n".join(
                [
                    f"{tint('dim', 'EMAIL    ')} {tint('cyan', contact.email, link)}",
                    f"{tint('dim', 'GITHUB   ')} {tint('cyan', contact.github_url, link)}",
                    f"{tint('dim', 'LOCATION ')} {safe(contact.location)}",
                ]
            ),
            classes="card contact-card",
        )
        card.border_title = "SECURE CHANNELS"
        yield card
        with Horizontal(id="contact-actions"):
            yield Button("COPY EMAIL", id="copy-email", classes="neon-button")
            yield Button("COPY GITHUB", id="copy-github", classes="neon-button")
            if self.web:
                yield Button("OPEN LINK: GITHUB", id="open-github", classes="neon-button")
                yield Button("OPEN LINK: EMAIL", id="open-email", classes="neon-button")
        if not self.web:
            yield Static(
                tint("dim", "Clickable links are available in the web build."), classes="caption"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Copy or open contact links."""
        contact = self.profile.contact
        if event.button.id == "copy-email":
            self.app.copy_to_clipboard(contact.email)
            self.notify("email copied to clipboard", title="UPLINK")
        elif event.button.id == "copy-github":
            self.app.copy_to_clipboard(contact.github_url)
            self.notify("GitHub URL copied to clipboard", title="UPLINK")
        elif event.button.id == "open-github" and self.web:
            self.app.open_url(contact.github_url)
        elif event.button.id == "open-email" and self.web:
            self.app.open_url(contact.mailto_url)


class TerminalSection(Vertical):
    """Hosts the sandboxed fake shell."""

    DEFAULT_CLASSES = "section"

    def __init__(self, shell: FakeShell, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.shell = shell

    def compose(self) -> ComposeResult:
        """The shell widget."""
        yield FakeShellWidget(self.shell, id="fake-shell")


class BlackIceSection(Section):
    """Admin-only easter egg. Entirely fictional lore."""

    def __init__(self, lore: Lore, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.lore = lore

    def compose(self) -> ComposeResult:
        """Skull, title and lore lines."""
        yield Static("\n".join(SKULL), classes="skull")
        yield Static(tint("danger", self.lore.blackice_title, "bold"), classes="blackice-title")
        yield Static(
            "\n".join(tint("green", line) for line in self.lore.blackice_body),
            classes="card blackice-body",
        )
