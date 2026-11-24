"""The "TOP SECRET" file on the profile screen: it looks like you shouldn't click it."""

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static

from snaizer_net.content import Overwatch
from snaizer_net.markup import tint
from snaizer_net.widgets.motion import motion_enabled

FLICKER_SECONDS = 0.8


class ClassifiedButton(Static, can_focus=True):
    """A classified stamp with a slowly flickering red frame. Click or Enter opens it."""

    BINDINGS = [Binding("enter", "open", "open file", show=False)]

    class Opened(Message):
        """Someone opened the file they were told not to."""

    def __init__(self, overwatch: Overwatch, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.overwatch = overwatch

    def on_mount(self) -> None:
        """Draw the stamp and start the slow flicker."""
        ow = self.overwatch
        self.update(
            f"{tint('danger', f'▓▓ {ow.button_title} ▓▓', 'bold')}\n"
            f"{tint('dim', 'FILE')} {tint('yellow', ow.file_id, 'bold')}  "
            f"{tint('dim', ow.button_note)}"
        )
        self.set_interval(FLICKER_SECONDS, self._flicker)

    def _flicker(self) -> None:
        if motion_enabled(self):
            self.toggle_class("-dim")
        else:
            self.remove_class("-dim")

    def on_click(self) -> None:
        """Open the file."""
        self.post_message(self.Opened())

    def action_open(self) -> None:
        """Enter opens the file."""
        self.post_message(self.Opened())
