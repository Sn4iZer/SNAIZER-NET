"""Terminal-looking front end for :class:`~snaizer_net.shell.commands.FakeShell`."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Input, Static

from snaizer_net.markup import safe, tint
from snaizer_net.shell.commands import Action, FakeShell
from snaizer_net.shell.tokenizer import MAX_INPUT

MAX_LINES = 400
MAX_HISTORY = 100


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
    """Scrollback plus a prompt line."""

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
        self.history: list[str] = []
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
        """Append markup lines to the scrollback."""
        self.lines.extend(lines)
        del self.lines[:-MAX_LINES]
        self.query_one("#shell-output", Static).update("\n".join(self.lines))
        self.query_one("#shell-scroll", VerticalScroll).scroll_end(animate=False)

    def run_command(self, line: str) -> None:
        """Echo ``line``, execute it in the sandbox and show the result."""
        self.write(self.shell.prompt + safe(line))
        if line.strip():
            self.history.append(line)
            del self.history[:-MAX_HISTORY]
        self._history_index = len(self.history)
        result = self.shell.execute(line)
        if result.action == "clear":
            self.lines.clear()
        self.write(*result.lines)
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
        if not self.history:
            return
        self._history_index = max(0, min(len(self.history), self._history_index + event.delta))
        field.value = (
            self.history[self._history_index] if self._history_index < len(self.history) else ""
        )
        field.cursor_position = len(field.value)

    def focus_input(self) -> None:
        """Focus the prompt."""
        self.query_one(ShellInput).focus()
