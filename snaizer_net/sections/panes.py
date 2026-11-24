"""Section widgets. Every fact comes from :class:`~snaizer_net.content.Profile`."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, ListItem, ListView, Static

from snaizer_net.assets.ascii import SKULL, TROPHY
from snaizer_net.config import ANIM_FPS
from snaizer_net.content import Lore, Profile, Project, parse_period
from snaizer_net.markup import safe, tint
from snaizer_net.shell.commands import FakeShell
from snaizer_net.timeline import KIND_COLOR, KIND_GLYPH, build_timeline, period_label
from snaizer_net.widgets.classified import ClassifiedButton
from snaizer_net.widgets.counter import CounterStat
from snaizer_net.widgets.decrypt_text import DecryptText
from snaizer_net.widgets.fake_shell import FakeShellWidget
from snaizer_net.widgets.glitch_label import GlitchBanner
from snaizer_net.widgets.ledger import LedgerEntry
from snaizer_net.widgets.motion import motion_enabled
from snaizer_net.widgets.project_card import ProjectCard
from snaizer_net.widgets.sensor_panel import SensorPanel
from snaizer_net.widgets.skill_bar import SkillBar
from snaizer_net.widgets.typewriter import Typewriter


class Section(VerticalScroll, can_focus=False):
    """Scrollable pane (mouse wheel / PgUp / PgDn); never steals arrow keys."""

    DEFAULT_CLASSES = "section"


def now_readout(profile: Profile) -> list[tuple[str, str]]:
    """``(label, markup)`` rows: what Mohammed is studying, his last role, top award."""
    rows: list[tuple[str, str]] = []
    if profile.education:
        edu = profile.education[0]
        period = parse_period(edu.period)
        label = "studying" if period and period.end is None else "graduated"
        rows.append((label, f"{safe(edu.degree)}{tint('dim', ', ' + edu.institution)}"))
    if profile.experience:
        exp = profile.experience[0]
        rows.append(
            (
                "last role",
                f"{safe(exp.title)}{tint('dim', ', ' + exp.organization)} "
                f"{tint('yellow', period_label(exp.period))}",
            )
        )
    if profile.awards:
        award = profile.awards[0]
        rows.append(
            (
                "top award",
                f"{safe(award.place)}{tint('dim', ', ' + award.title)} "
                f"{tint('yellow', str(award.year))}",
            )
        )
    return rows


class ProfileSection(Section):
    """Handle as the hero, then name, bio, a "now" readout, the file and the numbers."""

    def __init__(
        self, profile: Profile, lore: Lore, *, classified: bool = True, id: str | None = None
    ) -> None:
        super().__init__(id=id)
        self.profile = profile
        self.lore = lore
        self.classified = classified

    def compose(self) -> ComposeResult:
        """Hero, readout, counters and the simulated feed."""
        ident = self.profile.identity
        banner = GlitchBanner([[(ident.handle, "magenta")]], chance=0.0, id="profile-handle")
        banner.compact = True
        yield banner
        yield Static(
            f"{tint('text', ident.name, 'bold')}\n"
            f"{tint('cyan', ident.title)}{tint('dim', ', ' + ident.location)}",
            id="profile-name",
        )
        yield Typewriter(ident.bio, id="bio")
        yield Static(
            "\n".join(
                f"{tint('dim', label.ljust(10))} {markup}"
                for label, markup in now_readout(self.profile)
            ),
            id="profile-now",
        )
        if self.classified:
            yield ClassifiedButton(self.lore.overwatch, id="classified")
        stats = [
            (str(len(self.profile.projects)), "projects"),
            (str(len(self.profile.awards)), "awards"),
            *((item.value, item.label) for item in self.profile.highlights),
        ]
        with Horizontal(id="profile-stats"):
            for value, label in stats:
                yield CounterStat(value, label, classes="stat")
        yield SensorPanel(id="sensor-panel")

    def on_show(self) -> None:
        """A short glitch on the handle each time the profile opens."""
        self.query_one(GlitchBanner).glitch(3)


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
            f"{tint(KIND_COLOR[kind], KIND_GLYPH[kind])} {tint('dim', kind)}" for kind in KIND_COLOR
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
                f"{' ' * width}  {tint('dim', ' ' if last else '│')}   {tint('dim', entry.detail)}"
            )
        self.query_one("#timeline-body", Static).update("\n".join(lines))


class EducationSection(Section):
    """Degrees as ledger rows."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """One row per degree."""
        for edu in self.profile.education:
            yield LedgerEntry(
                period_label(edu.period), edu.degree, f"{edu.institution}, {edu.location}"
            )


class SkillsSection(Section):
    """Neon skill bars per category, plus spoken languages."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """A caption, then a heading and bars per category."""
        yield Static(
            tint("dim", "Bars show self-assessed, relative proficiency. Languages use CV levels."),
            classes="caption",
        )
        groups = [
            (category.name, [SkillBar(skill.name, skill.level) for skill in category.skills])
            for category in self.profile.skills
        ]
        groups.append(
            (
                "Spoken languages",
                [
                    SkillBar(lang.name, lang.bar, label=lang.level)
                    for lang in self.profile.languages
                ],
            )
        )
        for name, bars in groups:
            yield Static(tint("cyan", name, "bold"), classes="group-heading")
            yield Vertical(*bars, classes="skill-group")


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
        label = f"tag: {self.active_filter}" if self.active_filter else "all"
        project_list = self.query_one(ProjectList)
        project_list.border_title = f"{label} ({len(self.shown_projects)})"
        project_list.border_subtitle = "f filter"

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
    """Trophy art plus one card per award; the card frame encodes the placing."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """Trophy and cards side by side."""
        with Horizontal(id="awards-row"):
            yield Static("\n".join(TROPHY), classes="trophy")
            with Vertical(id="awards-cards"):
                for award in self.profile.awards:
                    rank = "-first" if award.place.lower().startswith("1st") else "-placed"
                    card = Static(
                        f"{tint('text', award.title, 'bold')}\n"
                        f"{tint('dim', award.organizer)}\n"
                        f"{safe(award.description)}",
                        classes=f"award-card {rank}",
                    )
                    card.border_title = f"★ {award.place}"
                    card.border_subtitle = str(award.year)
                    yield card


class ExperienceSection(Section):
    """Work and entrepreneurship entries as ledger rows."""

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """One row per entry."""
        for exp in self.profile.experience:
            yield LedgerEntry(period_label(exp.period), exp.title, exp.organization, exp.bullets)


class ContactSection(Section):
    """Contact channels, a sealed phone number and copy/open actions."""

    def __init__(self, profile: Profile, web: bool, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile
        self.web = web

    def compose(self) -> ComposeResult:
        """Label/value rows, then actions."""
        contact = self.profile.contact
        rows = [
            ("email", tint("cyan", contact.email, "underline")),
            ("github", tint("cyan", contact.github_url, "underline")),
            ("location", safe(contact.location)),
        ]
        for label, value in rows:
            with Horizontal(classes="contact-row"):
                yield Static(tint("dim", label), classes="contact-label")
                yield Static(value, classes="contact-value")
        if contact.phone_sealed:
            with Horizontal(classes="contact-row"):
                yield Static(tint("dim", "phone"), classes="contact-label")
                yield DecryptText(
                    lambda: contact.phone or "",
                    len(contact.phone or ""),
                    id="phone",
                    classes="contact-value",
                )
        with Horizontal(id="contact-actions"):
            if contact.phone_sealed:
                yield Button("Decrypt phone", id="decrypt-phone", compact=True)
            yield Button("Copy email", id="copy-email", compact=True)
            yield Button("Copy GitHub link", id="copy-github", compact=True)
            if self.web:
                yield Button("Open GitHub", id="open-github", compact=True)
                yield Button("Write an email", id="open-email", compact=True)
        if not self.web:
            yield Static(
                tint("dim", "In the browser version you can also open GitHub or start an email."),
                classes="caption",
            )

    def decrypt_phone(self) -> None:
        """Decode the phone number in place, then offer to copy it."""
        phone = self.query("#phone").results(DecryptText)
        target = next(iter(phone), None)
        if target is None or target.revealed or target.decoding:
            return

        def done() -> None:
            button = self.query_one("#decrypt-phone", Button)
            button.label = "Copy phone"
            self.notify("Phone decrypted", title="contact")

        target.reveal(done)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Decrypt, copy or open contact details."""
        contact = self.profile.contact
        button = event.button.id
        if button == "decrypt-phone":
            phone = self.query_one("#phone", DecryptText)
            if phone.revealed:
                self.app.copy_to_clipboard(phone.plain)
                self.notify("Phone copied", title="contact")
            else:
                self.decrypt_phone()
        elif button == "copy-email":
            self.app.copy_to_clipboard(contact.email)
            self.notify("Email copied", title="contact")
        elif button == "copy-github":
            self.app.copy_to_clipboard(contact.github_url)
            self.notify("GitHub link copied", title="contact")
        elif button == "open-github" and self.web:
            self.app.open_url(contact.github_url)
        elif button == "open-email" and self.web:
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
            classes="blackice-body",
        )
