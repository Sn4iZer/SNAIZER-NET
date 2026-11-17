"""Section widgets. Every fact comes from :class:`~snaizer_net.content.Profile`."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Label, ListItem, ListView, Static

from snaizer_net.assets.ascii import AVATAR, SKULL, TROPHY
from snaizer_net.content import Lore, Profile
from snaizer_net.markup import safe, tint
from snaizer_net.shell.commands import FakeShell
from snaizer_net.widgets.fake_shell import FakeShellWidget
from snaizer_net.widgets.project_card import ProjectCard
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
                yield Static(
                    f"{tint('cyan', value, 'bold')}\n{tint('dim', label)}", classes="stat-box"
                )


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


class ProjectsSection(Horizontal):
    """Project list on the left, dossier on the right."""

    DEFAULT_CLASSES = "section"

    def __init__(self, profile: Profile, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.profile = profile

    def compose(self) -> ComposeResult:
        """List and card."""
        items = [
            ListItem(
                Label(f"{tint('yellow', f'{index:02d}')} {safe(project.title)}"),
                classes="project-item",
            )
            for index, project in enumerate(self.profile.projects, start=1)
        ]
        project_list = ProjectList(*items, id="project-list")
        project_list.border_title = "MISSIONS"
        yield project_list
        with VerticalScroll(id="dossier-scroll", can_focus=False):
            yield ProjectCard(self.profile.projects[0], id="dossier")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Show the highlighted project collapsed."""
        index = event.list_view.index
        if index is not None:
            self.query_one(ProjectCard).show(self.profile.projects[index], index + 1)

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
