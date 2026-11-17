import pytest

from snaizer_net.auth_theater import LoginGate, Verdict, display_name


@pytest.mark.parametrize(("user", "password"), [("", ""), ("neo", ""), ("", "pw"), ("   ", "pw")])
def test_empty_fields_are_denied(user, password):
    outcome = LoginGate().attempt(user, password)
    assert outcome.verdict is Verdict.DENIED_EMPTY
    assert not outcome.granted


def test_weak_password_triggers_trace_joke_once_then_grants():
    gate = LoginGate()
    assert gate.attempt("neo", "1234").verdict is Verdict.TRACE_JOKE
    retry = gate.attempt("neo", "1234")
    assert retry.granted
    assert gate.attempts == 2


@pytest.mark.parametrize("password", ["12345", "123456", "0000", "password", "QWERTY"])
def test_other_weak_passwords_also_joke(password):
    assert LoginGate().attempt("neo", password).verdict is Verdict.TRACE_JOKE


def test_guest_guest_shows_hint():
    outcome = LoginGate().attempt("guest", "guest")
    assert outcome.granted
    assert outcome.show_hint
    assert not outcome.admin


def test_guest_with_other_password_has_no_hint():
    assert not LoginGate().attempt("guest", "hunter2").show_hint


@pytest.mark.parametrize("user", ["snaizer", "admin", "SnAiZeR", "  admin  "])
def test_admin_users_get_badge(user):
    outcome = LoginGate().attempt(user, "anything")
    assert outcome.granted
    assert outcome.admin


def test_any_other_credentials_succeed():
    outcome = LoginGate().attempt("case", "wintermute")
    assert outcome.granted
    assert outcome.user == "case"
    assert not outcome.admin
    assert not outcome.show_hint


def test_empty_attempt_does_not_consume_the_joke():
    gate = LoginGate()
    gate.attempt("", "")
    assert gate.attempt("neo", "1234").verdict is Verdict.TRACE_JOKE


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("neo", "neo"),
        ("[$neon-danger]evil", "neon-dangerevil"),
        ("a" * 40, "a" * 16),
        ("!!!", "runner"),
        ("  trinity.99 ", "trinity.99"),
    ],
)
def test_display_name_is_sanitized(raw, shown):
    assert display_name(raw) == shown
