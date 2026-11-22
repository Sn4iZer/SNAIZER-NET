"""Screen 3: the main HUD with navigation and all portfolio sections."""

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import ContentSwitcher, Static

from snaizer_net.config import NARROW_WIDTH
from snaizer_net.content import Lore, Profile
from snaizer_net.markup import tint
from snaizer_net.navigation import SECTIONS, visible_sections
from snaizer_net.screens._app import snaizer_app
from snaizer_net.screens.overlays import HelpScreen, MatrixScreen
from snaizer_net.sections import (
    AwardsSection,
    BlackIceSection,
    ContactSection,
    EducationSection,
    ExperienceSection,
    ProfileSection,
    ProjectsSection,
    SkillsSection,
    TerminalSection,
    TimelineSection,
)
from snaizer_net.shell.commands import FakeShell
from snaizer_net.themes import USER_THEMES
from snaizer_net.widgets.fake_shell import FakeShellWidget
from snaizer_net.widgets.glitch_label import GlitchLabel
from snaizer_net.widgets.nav import NavItem, Sidebar, TabStrip
from snaizer_net.widgets.scanline import ScanLine
from snaizer_net.widgets.status_bar import KeyHints, StatusBar


class MainScreen(Screen[None]):
    """Status bar, navigation, content pane and key hints."""

    AUTO_FOCUS = ""  # disabled: focus is managed per section in show_section()
    BINDINGS = [
        *(Binding(spec.key, f"goto('{spec.id}')", spec.title, show=False) for spec in SECTIONS),
        Binding("down,j,tab", "move(1)", "next section", show=False),
        Binding("up,k,shift+tab", "move(-1)", "previous section", show=False),
        Binding("pagedown", "scroll_section(1)", "scroll down", show=False),
        Binding("pageup", "scroll_section(-1)", "scroll up", show=False),
        Binding("m", "matrix", "matrix", show=False),
        Binding("d", "decrypt_phone", "decrypt phone", show=False),
        Binding("slash", "app.command_palette", "search", show=False),
        Binding("question_mark", "help", "help", show=False),
        Binding("q", "quit", "quit", show=False),
    ]
    PULSE_SECONDS = 0.6

    def __init__(self, profile: Profile, lore: Lore, user: str, admin: bool) -> None:
        super().__init__()
        self.profile = profile
        self.lore = lore
        self.user = user
        self.admin = admin
        self.sections = visible_sections(admin)
        self.current = self.sections[0].id

    def compose(self) -> ComposeResult:
        """Build the HUD."""
        app = snaizer_app(self)
        shell = FakeShell(
            self.profile,
            self.lore,
            user=self.user,
            admin=self.admin,
            themes=USER_THEMES,
            current_theme=app.theme,
        )
        yield StatusBar(self.user, self.admin, app.config.mode, id="status")
        yield TabStrip(self.sections, id="tabstrip")
        with Horizontal(id="body"):
            yield Sidebar(self.sections, self.lore.hostname, id="sidebar")
            with Vertical(id="pane"):
                with Vertical(id="section-head"):
                    yield GlitchLabel(
                        "", prefix=tint("magenta", "◢◤ ", "bold"), chance=0.0, id="section-title"
                    )
                    yield Static("", id="section-blurb")
                with ContentSwitcher(initial=self.current, id="switcher"):
                    yield ProfileSection(self.profile, id="profile")
                    yield EducationSection(self.profile, id="education")
                    yield SkillsSection(self.profile, id="skills")
                    yield ProjectsSection(self.profile, id="projects")
                    yield AwardsSection(self.profile, id="awards")
                    yield ExperienceSection(self.profile, id="experience")
                    yield ContactSection(self.profile, app.config.is_web, id="contact")
                    yield TerminalSection(shell, id="terminal")
                    yield TimelineSection(self.profile, id="timeline")
                    if self.admin:
                        yield BlackIceSection(self.lore, id="blackice")
                yield ScanLine(id="scanline")  # last child, so it draws on top
        yield KeyHints(id="key-hints")

    def on_mount(self) -> None:
        """Apply the layout for the current width and show the first section."""
        self._apply_width(self.app.size.width)
        self.show_section(self.current, sweep=False)
        self.set_interval(self.PULSE_SECONDS, self._pulse)

    def _pulse(self) -> None:
        """Breathe the active nav item and dossier border (CSS keyed on -pulse)."""
        if snaizer_app(self).motion_enabled:
            self.toggle_class("-pulse")
        else:
            self.remove_class("-pulse")

    def on_resize(self, event: events.Resize) -> None:
        """Collapse the sidebar into a tab strip on narrow terminals."""
        self._apply_width(event.size.width)

    def _apply_width(self, width: int) -> None:
        self.set_class(width < NARROW_WIDTH, "-narrow")

    def show_section(self, section_id: str, sweep: bool = True) -> None:
        """Switch the content pane to ``section_id`` and update navigation."""
        spec = next((s for s in self.sections if s.id == section_id), None)
        if spec is None:
            return
        if sweep and section_id != self.current:
            self.query_one(ScanLine).sweep()
        self.current = section_id
        self.query_one(ContentSwitcher).current = section_id
        self.query_one("#section-title", GlitchLabel).set_text(spec.path, glitch=True)
        blurb = spec.blurb
        if spec.id == "contact" and self.profile.contact.phone_sealed is None:
            blurb = "Email and GitHub."
        self.query_one("#section-blurb", Static).update(tint("dim", blurb))
        self.query_one(Sidebar).set_active(section_id)
        self.query_one(TabStrip).set_active(section_id)
        self.query_one(KeyHints).set_context(section_id)
        if section_id == "terminal":
            self.query_one(FakeShellWidget).focus_input()
        elif section_id == "projects":
            self.query_one(ProjectsSection).focus_list()
        else:
            self.set_focus(None)

    def current_section(self) -> Widget:
        """The widget currently displayed in the content pane."""
        return self.query_one(f"#{self.current}")

    def action_goto(self, section_id: str) -> None:
        """Jump to a section by id (ignored if not visible to this runner)."""
        self.show_section(section_id)

    def action_move(self, delta: int) -> None:
        """Move to the previous / next section, wrapping around."""
        ids = [spec.id for spec in self.sections]
        index = (ids.index(self.current) + delta) % len(ids)
        self.show_section(ids[index])

    def action_scroll_section(self, direction: int) -> None:
        """Scroll the current section by a page."""
        section = self.current_section()
        if direction > 0:
            section.scroll_page_down()
        else:
            section.scroll_page_up()

    def open_project(self, slug: str) -> None:
        """Jump to PROJECTS and expand the dossier ``slug``."""
        self.show_section("projects")
        self.call_later(self.query_one(ProjectsSection).open_project, slug)

    def action_decrypt_phone(self) -> None:
        """``d`` decrypts the sealed phone number (jumping to contact first)."""
        if self.profile.contact.phone_sealed is None:
            return
        self.show_section("contact")
        self.query_one(ContactSection).decrypt_phone()

    def filter_projects(self, tag: str | None) -> None:
        """Jump to PROJECTS filtered by ``tag`` (``None`` = all)."""
        self.show_section("projects")
        self.call_later(self.query_one(ProjectsSection).set_filter, tag)

    def action_matrix(self) -> None:
        """Enter matrix rain mode."""
        self.app.push_screen(MatrixScreen())

    def action_help(self) -> None:
        """Open the help overlay."""
        self.app.push_screen(HelpScreen())

    def action_quit(self) -> None:
        """Quit cleanly."""
        self.app.exit()

    def on_nav_item_selected(self, message: NavItem.Selected) -> None:
        """Mouse navigation."""
        self.show_section(message.section_id)

    def on_fake_shell_widget_action_requested(
        self, message: FakeShellWidget.ActionRequested
    ) -> None:
        """Apply UI side effects requested by the fake shell."""
        if message.action == "exit":
            self.app.exit()
        elif message.action == "matrix":
            self.action_matrix()
        elif message.action == "open_project" and message.argument:
            self.open_project(message.argument)
        elif message.action == "theme" and message.argument:
            snaizer_app(self).set_neon_theme(message.argument)
