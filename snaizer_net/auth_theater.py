"""The fake login's decision logic.

This is theater: nothing is ever checked against a real secret, file or
system account. Any non-empty credentials eventually get in.
"""

import re
from dataclasses import dataclass
from enum import Enum

ADMIN_USERS = frozenset({"snaizer", "admin"})
WEAK_PASSWORDS = frozenset({"1234", "12345", "123456", "0000", "password", "qwerty"})
DEFAULT_USER = "runner"
_SAFE_USER = re.compile(r"[^A-Za-z0-9_.-]")


class Verdict(Enum):
    """What the gate decided."""

    DENIED_EMPTY = "denied_empty"
    TRACE_JOKE = "trace_joke"
    GRANTED = "granted"


@dataclass(frozen=True)
class LoginOutcome:
    """Result of one login attempt."""

    verdict: Verdict
    user: str = DEFAULT_USER
    admin: bool = False
    show_hint: bool = False

    @property
    def granted(self) -> bool:
        """True when the runner is let in."""
        return self.verdict is Verdict.GRANTED


def display_name(username: str) -> str:
    """Sanitize a typed username for display (no markup, short, printable)."""
    cleaned = _SAFE_USER.sub("", username.strip())[:16]
    return cleaned or DEFAULT_USER


class LoginGate:
    """Stateful wrapper so the ``1234`` joke only fires once per session."""

    def __init__(self) -> None:
        self.attempts = 0
        self.joked = False

    def attempt(self, username: str, password: str) -> LoginOutcome:
        """Evaluate one attempt.

        Rules, in order:

        1. empty username or password: denied (biometric mismatch);
        2. a weak-looking password on the first such try: fake trace joke;
        3. everything else is granted. ``snaizer``/``admin`` get the ADMIN
           badge and ``guest``/``guest`` gets a hint line.
        """
        self.attempts += 1
        user = username.strip()
        if not user or not password:
            return LoginOutcome(Verdict.DENIED_EMPTY)
        if password.strip().lower() in WEAK_PASSWORDS and not self.joked:
            self.joked = True
            return LoginOutcome(Verdict.TRACE_JOKE)
        return LoginOutcome(
            Verdict.GRANTED,
            user=display_name(user),
            admin=user.lower() in ADMIN_USERS,
            show_hint=user.lower() == "guest" and password == "guest",
        )
