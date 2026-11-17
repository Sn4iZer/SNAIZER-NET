"""Terminal-looking front end for :class:`~snaizer_net.shell.commands.FakeShell`."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.timer import Timer
from textual.widgets import Input, Static

from snaizer_net.config import ANIM_FPS
from snaizer_net.markup import safe, tint
from snaizer_net.shell.commands import Action, FakeShell
from snaizer_net.shell.tokenizer import MAX_INPUT
from snaizer_net.widgets.motion import motion_enabled

MAX_LINES = 400


class ShellInput(Input):
    """Prompt input with history, tab completion and an escape hatch."""

    BINDINGS = [
        Binding("up", "history(-1)", "previous", show=False),
        Binding("down", "history(1)", "next", show=False),
        Binding("tab", "complete", "complete", show=False),
        Binding("escape", "leave", "leave terminal", show=False),
    ]

    class Navigate(Message):
        """Request to move through history or complete the current line."""

        def __init__(self, kind: str, delta: int = 0) -> None:
            super().__init__()
            self.kind = kind
            self.delta = delta

    def action_history(self, delta: int) -> None:
        """Browse command history."""
        self.post_message(self.Navigate("history", delta))

    def action_complete(self) -> None:
        """Tab-complete the current line."""
        self.post_message(self.Navigate("complete"))

    def action_leave(self) -> None:
        """Give focus back to the screen so number keys navigate again."""
        self.screen.set_focus(None)


class FakeShellWidget(Vertical):
    """Scrollback plus a prompt line; command output streams in line by line."""

    class ActionRequested(Message):
        """The shell asked the UI to do something (clear excluded)."""

        def __init__(self, action: Action, argument: str | None) -> None:
            super().__init__()
            self.action = action
            self.argument = argument

    def __init__(self, shell: FakeShell, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.shell = shell
        self.lines: list[str] = []
        self.pending: list[str] = []
        self._pace = 1
        self._stream_timer: Timer | None = None
        self._history_index = 0

    def compose(self) -> ComposeResult:
        """Output area and prompt."""
        with VerticalScroll(id="shell-scroll"):
            yield Static("", id="shell-output")
        with Horizontal(id="shell-prompt-row"):
            yield Static(self.shell.prompt, id="shell-prompt")
            yield ShellInput(placeholder="type 'help'", max_length=MAX_INPUT, id="shell-input")

    def on_mount(self) -> None:
        """Print the message of the day."""
        self.write(
            tint("green", self.shell.lore.shell_motd),
            tint("dim", "Type 'help' to list programs. ESC leaves the terminal."),
            "",
        )

    def write(self, *lines: str) -> None:
        """Append markup lines to the scrollback immediately."""
        self.lines.extend(lines)
        del self.lines[:-MAX_LINES]
        self._render_lines()

    def _render_lines(self) -> None:
        self.query_one("#shell-output", Static).update("\n".join(self.lines))
        self.query_one("#shell-scroll", VerticalScroll).scroll_end(animate=False)

    def stream(self, lines: tuple[str, ...], pace: int) -> None:
        """Reveal ``lines`` a few per frame (instantly without motion)."""
        if not motion_enabled(self) or len(lines) <= pace:
            self.write(*lines)
            return
        self.pending.extend(lines)
        self._pace = max(1, pace)
        if self._stream_timer is None:
            self._stream_timer = self.set_interval(1 / ANIM_FPS, self._stream_tick)

    def _stream_tick(self) -> None:
        batch, self.pending = self.pending[: self._pace], self.pending[self._pace :]
        self.write(*batch)
        if not self.pending:
            self._stop_stream()

    def flush(self) -> None:
        """Print any output still streaming."""
        if self.pending:
            batch, self.pending = self.pending, []
            self.write(*batch)
        self._stop_stream()

    def _stop_stream(self) -> None:
        if self._stream_timer is not None:
            self._stream_timer.stop()
            self._stream_timer = None

    def run_command(self, line: str) -> None:
        """Echo ``line``, execute it in the sandbox and show the result."""
        self.flush()
        self.write(self.shell.prompt + safe(line))
        result = self.shell.execute(line)
        self._history_index = len(self.shell.history)
        if result.action == "clear":
            self.lines.clear()
            self._render_lines()
        self.stream(result.lines, result.pace)
        self.query_one("#shell-prompt", Static).update(self.shell.prompt)
        if result.action and result.action != "clear":
            self.post_message(self.ActionRequested(result.action, result.argument))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run the submitted line."""
        event.stop()
        event.input.value = ""
        self.run_command(event.value)

    def on_shell_input_navigate(self, event: ShellInput.Navigate) -> None:
        """Handle history browsing and completion."""
        event.stop()
        field = self.query_one(ShellInput)
        if event.kind == "complete":
            completed = self.shell.complete(field.value)
            if completed is not None:
                field.value = completed
                field.cursor_position = len(completed)
            return
        history = self.shell.history
        if not history:
            return
        self._history_index = max(0, min(len(history), self._history_index + event.delta))
        field.value = history[self._history_index] if self._history_index < len(history) else ""
        field.cursor_position = len(field.value)

    def focus_input(self) -> None:
        """Focus the prompt."""
        self.query_one(ShellInput).focus()
