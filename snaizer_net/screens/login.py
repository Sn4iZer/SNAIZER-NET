"""Screen 2: the FAKE neural-link login. Pure theater, never checks real secrets."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Input, Static

from snaizer_net.auth_theater import LoginGate, LoginOutcome, Verdict
from snaizer_net.config import ANIM_FPS
from snaizer_net.content import Lore
from snaizer_net.markup import tint
from snaizer_net.screens._app import snaizer_app
from snaizer_net.widgets.glitch_label import LOGO_LINES, GlitchBanner
from snaizer_net.widgets.hex_stream import HexStream
from snaizer_net.widgets.motion import motion_enabled

GRANTED_LINES = [[("ACCESS", "green")], [("GRANTED", "green")]]
SHAKE_OFFSETS = (3, -3, 2, -2, 1, 0)


class LoginScreen(Screen[None]):
    """Username + masked passphrase. Any non-empty credentials get in."""

    def __init__(self, lore: Lore) -> None:
        super().__init__()
        self.lore = lore
        self.gate = LoginGate()
        self.busy = False

    def compose(self) -> ComposeResult:
        """Logo, auth box, and the hidden decrypt / granted stages."""
        with Vertical(id="login-wrap"):
            yield GlitchBanner(LOGO_LINES, id="login-logo")
            yield Static(
                tint("magenta", "NEURAL-LINK AUTHENTICATION", "bold")
                + tint("dim", " // ")
                + tint("danger", "RESTRICTED NODE", "bold"),
                id="login-title",
            )
            with Vertical(id="login-box"):
                yield Static(tint("cyan", "IDENT ▸", "bold"), classes="login-label")
                yield Input(placeholder="runner id", max_length=32, id="login-user")
                yield Static(tint("cyan", "PASSPHRASE ▸", "bold"), classes="login-label")
                yield Input(placeholder="••••••", password=True, max_length=64, id="login-pass")
                yield Static("", id="login-status")
                yield Static(
                    "   ".join(
                        f"{tint('cyan', key, 'bold')} {tint('dim', action)}"
                        for key, action in (
                            ("ENTER", "jack in"),
                            ("TAB", "switch field"),
                            ("ctrl+c", "abort"),
                        )
                    ),
                    id="login-help",
                )
            yield HexStream(id="decrypt")
            yield GlitchBanner(GRANTED_LINES, chance=0.0, id="granted")

    def on_mount(self) -> None:
        """Size the logo and focus the username field."""
        self.query_one("#login-logo", GlitchBanner).compact = True
        self.query_one("#granted", GlitchBanner).compact = self.app.size.height < 30
        self.query_one("#decrypt").display = False
        self.query_one("#granted").display = False
        self.query_one("#login-user", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """ENTER on the username moves on; ENTER on the passphrase submits."""
        event.stop()
        if self.busy:
            return
        if event.input.id == "login-user":
            self.query_one("#login-pass", Input).focus()
            return
        self.submit()

    def submit(self) -> None:
        """Evaluate the current credentials and play the matching scene."""
        user = self.query_one("#login-user", Input).value
        password = self.query_one("#login-pass", Input).value
        outcome = self.gate.attempt(user, password)
        if outcome.verdict is Verdict.DENIED_EMPTY:
            self._deny()
        elif outcome.verdict is Verdict.TRACE_JOKE:
            self._trace_joke()
        else:
            self._grant(outcome)

    # -- scenes ----------------------------------------------------------

    def _status(self, markup: str) -> None:
        self.query_one("#login-status", Static).update(markup)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        for field in self.query(Input):
            field.disabled = not enabled

    def _deny(self) -> None:
        self._status(tint("danger", f"✖ {self.lore.login_denied_empty}", "bold"))
        box = self.query_one("#login-box")
        box.add_class("-denied")
        self.set_timer(0.6, lambda: box.remove_class("-denied"))
        self._shake()

    def _shake(self) -> None:
        if not motion_enabled(self):
            return
        box = self.query_one("#login-box")
        offsets = list(SHAKE_OFFSETS)

        def step() -> None:
            box.styles.offset = (offsets.pop(0), 0)
            if not offsets:
                timer.stop()

        timer = self.set_interval(1 / ANIM_FPS, step)

    def _trace_joke(self) -> None:
        self.busy = True
        self._set_inputs_enabled(False)
        self.query_one("#login-box").add_class("-denied")
        self._shake()
        base = tint("danger", "✖ ACCESS DENIED, trace initiated", "bold")
        abort = tint("green", self.lore.login_trace_abort)
        if not motion_enabled(self):
            self._status(f"{base} {tint('yellow', '3... 2... 1...')}\n{abort}")
            self.set_timer(0.5, self._end_trace)
            return
        steps = [
            f"{base} {tint('yellow', count)}" for count in ("3...", "3... 2...", "3... 2... 1...")
        ]
        steps.append(f"{steps[-1]}\n{abort}")

        def step() -> None:
            self._status(steps.pop(0))
            if not steps:
                timer.stop()
                self.set_timer(1.2, self._end_trace)

        step()
        timer = self.set_interval(0.7, step)

    def _end_trace(self) -> None:
        self.busy = False
        self.query_one("#login-box").remove_class("-denied")
        self._set_inputs_enabled(True)
        password = self.query_one("#login-pass", Input)
        password.value = ""
        password.focus()

    def _grant(self, outcome: LoginOutcome) -> None:
        self.busy = True
        self._set_inputs_enabled(False)
        self.query_one("#login-box").add_class("-granted")
        if outcome.show_hint:
            self._status(tint("yellow", self.lore.login_hint, "bold"))
            self.set_timer(1.5, lambda: self._decrypt(outcome))
        else:
            self._status(tint("green", "✔ identity accepted", "bold"))
            self.set_timer(0.4, lambda: self._decrypt(outcome))

    def _decrypt(self, outcome: LoginOutcome) -> None:
        self.query_one("#login-box").display = False
        stream = self.query_one("#decrypt", HexStream)
        stream.display = True
        stream.run(1.6, lambda: self._show_granted(outcome))

    def _show_granted(self, outcome: LoginOutcome) -> None:
        self.query_one("#decrypt").display = False
        banner = self.query_one("#granted", GlitchBanner)
        banner.display = True
        banner.glitch(4)
        self.set_timer(1.2, lambda: snaizer_app(self).enter_main(outcome.user, outcome.admin))
