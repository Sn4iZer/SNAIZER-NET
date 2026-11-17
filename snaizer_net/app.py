"""The SNAIZER//NET Textual application and its screen routing."""

import os

from textual import events
from textual.app import App
from textual.binding import Binding
from textual.screen import Screen

from snaizer_net.config import MIN_HEIGHT, MIN_WIDTH, RunConfig
from snaizer_net.content import Lore, Profile
from snaizer_net.palette import SnaizerCommands
from snaizer_net.screens.boot import BootScreen
from snaizer_net.screens.login import LoginScreen
from snaizer_net.screens.main import MainScreen
from snaizer_net.screens.overlays import TooSmallScreen
from snaizer_net.themes import (
    DEFAULT_THEME,
    LOW_COLOR_THEME,
    PALETTES,
    all_themes,
    is_low_color_terminal,
    theme_variables,
)


class SnaizerApp(App[None]):
    """Boot -> fake login -> main HUD."""

    CSS_PATH = "theme.tcss"
    TITLE = "SNAIZER//NET"
    COMMANDS = {SnaizerCommands}
    COMMAND_PALETTE_BINDING = "ctrl+p"
    BINDINGS = [Binding("ctrl+c", "quit", "quit", show=False, priority=True)]

    def __init__(self, config: RunConfig, profile: Profile, lore: Lore) -> None:
        super().__init__()
        self.config = config
        self.profile = profile
        self.lore = lore
        self.user = ""
        self.admin = False
        self._too_small = False
        self._animations = config.animations
        for theme in all_themes():
            self.register_theme(theme)
        self.theme = self.initial_theme()

    def initial_theme(self) -> str:
        """Pick the 16-color palette on limited terminals, neon-night otherwise."""
        if self.config.colors == "16":
            return LOW_COLOR_THEME
        if (
            self.config.colors == "auto"
            and not self.config.is_web
            and is_low_color_terminal(os.environ)
        ):
            return LOW_COLOR_THEME
        return DEFAULT_THEME

    def get_theme_variable_defaults(self) -> dict[str, str]:
        """Defaults so ``$neon-*`` always resolves while the stylesheet is parsed."""
        return theme_variables(PALETTES[DEFAULT_THEME])

    @property
    def motion_enabled(self) -> bool:
        """Animations run unless disabled by flag or the terminal is too small."""
        return self._animations and not self._too_small

    def toggle_animations(self) -> None:
        """Switch animations on/off at runtime (command palette)."""
        self._animations = not self._animations
        state = "on" if self._animations else "off"
        self.notify(f"animations {state}", title="ACCESSIBILITY")

    def action_command_palette(self) -> None:
        """Open the palette only on the main HUD (not during boot / login)."""
        if isinstance(self.screen, MainScreen):
            super().action_command_palette()

    def on_mount(self) -> None:
        """Start with the boot sequence (or straight to the HUD with --skip-intro)."""
        if self.config.skip_intro:
            self.enter_main("runner", admin=False)
        else:
            self.push_screen(BootScreen(self.lore))
        self._check_size(*self.size)

    def on_resize(self, event: events.Resize) -> None:
        """Show / hide the "enlarge your terminal" overlay."""
        self._check_size(*event.size)

    def _check_size(self, width: int, height: int) -> None:
        too_small = width < MIN_WIDTH or height < MIN_HEIGHT
        if too_small and not self._too_small:
            self._too_small = True
            self.push_screen(TooSmallScreen())
        elif not too_small and self._too_small:
            self._too_small = False
            if isinstance(self.screen, TooSmallScreen):
                self.pop_screen()

    def _swap_to(self, screen: Screen[None]) -> None:
        """Replace the current stage screen, keeping the size overlay on top."""
        overlay = isinstance(self.screen, TooSmallScreen)
        if overlay:
            self.pop_screen()
        if len(self.screen_stack) > 1:
            self.switch_screen(screen)
        else:
            self.push_screen(screen)
        if overlay:
            self.push_screen(TooSmallScreen())

    def show_login(self) -> None:
        """Boot finished: show the fake login."""
        self._swap_to(LoginScreen(self.lore))

    def enter_main(self, user: str, admin: bool) -> None:
        """Login granted (or intro skipped): show the main HUD."""
        self.user, self.admin = user, admin
        self._swap_to(MainScreen(self.profile, self.lore, user, admin))

    def set_neon_theme(self, name: str) -> bool:
        """Switch palette; returns False for unknown names."""
        if name not in PALETTES:
            return False
        self.theme = name
        return True
