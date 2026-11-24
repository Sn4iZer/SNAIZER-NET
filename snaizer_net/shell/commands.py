"""The fake shell: a pure, in-memory command table.

Security model: every command is a Python method in :attr:`FakeShell.commands`.
There is no ``subprocess``, no ``eval``/``exec`` and no real filesystem
access; input is only ever tokenized and looked up in a dict. Output is
Textual markup in which every dynamic string goes through :func:`safe`.
"""

import posixpath
import random
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from snaizer_net.assets.ascii import NEOFETCH_LOGO
from snaizer_net.auth_theater import DEFAULT_USER
from snaizer_net.content import Lore, Profile
from snaizer_net.markup import safe, tint
from snaizer_net.shell.tokenizer import tokenize
from snaizer_net.shell.vfs import HOME, build_vfs
from snaizer_net.themes import DEFAULT_THEME, USER_THEMES
from snaizer_net.timeline import KIND_COLOR, KIND_GLYPH, build_timeline

Action = Literal["clear", "exit", "matrix", "theme", "open_project", "classified"]
NEOFETCH_VALUE_WIDTH = 44
MAX_HISTORY = 100
MAX_GREP_MATCHES = 30
DEFAULT_PACE = 3

FORBIDDEN = frozenset(
    {
        "bash", "chmod", "chown", "curl", "dd", "eval", "exec", "kill", "mkfs", "mv",
        "nc", "ncat", "perl", "python", "python3", "reboot", "rm", "scp", "sh",
        "shutdown", "ssh", "su", "sudo", "telnet", "vi", "vim", "wget", "zsh",
    }
)  # fmt: skip


@dataclass(frozen=True)
class ShellResult:
    """Output of one command: markup lines, an optional UI action, a streaming pace."""

    lines: tuple[str, ...] = ()
    action: Action | None = None
    argument: str | None = None
    pace: int = DEFAULT_PACE
    """Lines revealed per animation frame when the UI streams the output."""


@dataclass(frozen=True)
class Command:
    """A registered fake-shell command."""

    handler: Callable[[list[str]], ShellResult]
    usage: str
    summary: str


def _out(*lines: str, action: Action | None = None, argument: str | None = None) -> ShellResult:
    return ShellResult(tuple(lines), action, argument)


def _bar(level: int, width: int = 20) -> str:
    filled = round(level / 100 * width)
    return tint("cyan", "█" * filled) + tint("dim", "░" * (width - filled))


class FakeShell:
    """A sandboxed, theatrical shell over the portfolio content."""

    def __init__(
        self,
        profile: Profile,
        lore: Lore,
        *,
        user: str = DEFAULT_USER,
        admin: bool = False,
        themes: Sequence[str] = USER_THEMES,
        current_theme: str = DEFAULT_THEME,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.profile = profile
        self.lore = lore
        self.user = user
        self.admin = admin
        self.themes = tuple(themes)
        self.current_theme = current_theme
        self.cwd = HOME
        self.vfs = build_vfs(profile, lore, admin=admin)
        self._rng = rng or random.Random()
        self._clock = clock
        self._started = clock()
        self.history: list[str] = []
        self.commands: dict[str, Command] = {
            "help": Command(self._help, "help", "list available programs"),
            "whoami": Command(self._whoami, "whoami", "print your runner identity"),
            "ls": Command(self._ls, "ls [path]", "list files"),
            "cd": Command(self._cd, "cd [path]", "change directory"),
            "pwd": Command(self._pwd, "pwd", "print working directory"),
            "cat": Command(self._cat, "cat <file>...", "print a file"),
            "echo": Command(self._echo, "echo <text>", "print text (no expansion, ever)"),
            "grep": Command(self._grep, "grep <text>", "search every file for text"),
            "projects": Command(self._projects, "projects", "list mission dossiers"),
            "open": Command(self._open, "open <n|slug>", "open a project dossier"),
            "timeline": Command(self._timeline, "timeline", "chronological career log"),
            "skills": Command(self._skills, "skills", "show skill matrix"),
            "contact": Command(self._contact, "contact", "show contact channels"),
            "decrypt": Command(self._decrypt, "decrypt phone", "reveal the sealed phone number"),
            "neofetch": Command(self._neofetch, "neofetch", "system info, runner style"),
            "fortune": Command(self._fortune, "fortune", "a byte of runner wisdom"),
            "hack": Command(self._hack, "hack", "totally real intrusion (fiction)"),
            "history": Command(self._history, "history", "list previous commands"),
            "matrix": Command(self._matrix, "matrix", "enter the rain"),
            "classified": Command(
                self._classified,
                "classified",
                f"restricted file {lore.overwatch.file_id} (do not open)",
            ),
            "theme": Command(self._theme, "theme [name]", "list or switch color themes"),
            "clear": Command(self._clear, "clear", "clear the screen"),
            "exit": Command(self._exit, "exit", "disconnect from the node"),
        }

    @property
    def prompt(self) -> str:
        """Markup for the prompt, e.g. ``runner@snaizer-net:~$``."""
        where = "~" + self.cwd[len(HOME) :] if self.cwd.startswith(HOME) else self.cwd
        user_color = "yellow" if self.admin else "green"
        return (
            f"{tint(user_color, self.user, 'bold')}{tint('dim', '@')}"
            f"{tint('magenta', self.lore.hostname)}{tint('dim', ':')}"
            f"{tint('cyan', where)}{tint('dim', '$')} "
        )

    def execute(self, line: str) -> ShellResult:
        """Run one line of input against the command table."""
        tokens = tokenize(line.strip())
        if not tokens:
            return ShellResult()
        self.history.append(line.strip())
        del self.history[:-MAX_HISTORY]
        name, args = tokens[0], tokens[1:]
        command = self.commands.get(name)
        if command is not None:
            return command.handler(args)
        if name == "sudo":
            return _out(
                tint("danger", self.lore.shell_sudo.format(user=self.user), "bold"),
                tint("dim", "Nothing was executed."),
            )
        if posixpath.basename(name) in FORBIDDEN:
            template = self._rng.choice(self.lore.shell_forbidden)
            return _out(tint("danger", template.format(cmd=name[:40]), "bold"))
        template = self._rng.choice(self.lore.shell_unknown)
        return _out(tint("yellow", template.format(cmd=name[:40])))

    def complete(self, text: str) -> str | None:
        """Tab-complete a command name or a path argument; ``None`` if ambiguous."""
        tokens = text.split(" ")
        if len(tokens) == 1:
            matches = [name for name in self.commands if name.startswith(tokens[0])]
            return matches[0] + " " if len(matches) == 1 else None
        partial = tokens[-1]
        if "/" in partial:
            base, _, stem = partial.rpartition("/")
            directory = self.vfs.resolve(base or "/", self.cwd)
            prefix = base + "/"
        else:
            stem, directory, prefix = partial, self.cwd, ""
        if not self.vfs.is_dir(directory):
            return None
        matches = [entry for entry in self.vfs.listdir(directory) if entry.startswith(stem)]
        if len(matches) != 1:
            return None
        return " ".join([*tokens[:-1], prefix + matches[0]])

    # -- commands --------------------------------------------------------

    def _help(self, args: list[str]) -> ShellResult:
        width = max(len(cmd.usage) for cmd in self.commands.values())
        lines = [tint("magenta", "AVAILABLE PROGRAMS", "bold")]
        lines += [
            f"  {tint('cyan', cmd.usage.ljust(width))}  {tint('dim', cmd.summary)}"
            for cmd in self.commands.values()
        ]
        lines.append(tint("dim", "TAB completes, UP/DOWN browse history, ESC leaves the terminal."))
        return _out(*lines)

    def _whoami(self, args: list[str]) -> ShellResult:
        badge = f" {tint('yellow', '[ADMIN]', 'bold')}" if self.admin else ""
        clearance = "sysop (fictional)" if self.admin else "guest"
        return _out(
            f"{tint('green', self.user, 'bold')}{badge}",
            tint("dim", f"visitor on {self.profile.identity.name}'s node, clearance: {clearance}"),
        )

    def _ls(self, args: list[str]) -> ShellResult:
        target = self.vfs.resolve(args[0] if args else ".", self.cwd)
        if self.vfs.read(target) is not None:
            return _out(safe(posixpath.basename(target)))
        if not self.vfs.is_dir(target):
            return _out(tint("danger", f"ls: {args[0]}: no such file or directory"))
        entries = self.vfs.listdir(target)
        return _out(
            "  ".join(
                tint("cyan", name, "bold") if name.endswith("/") else safe(name) for name in entries
            )
        )

    def _cd(self, args: list[str]) -> ShellResult:
        target = self.vfs.resolve(args[0] if args else HOME, self.cwd)
        if not self.vfs.is_dir(target):
            return _out(tint("danger", f"cd: {args[0]}: no such directory"))
        self.cwd = target
        return ShellResult()

    def _pwd(self, args: list[str]) -> ShellResult:
        return _out(safe(self.cwd))

    def _cat(self, args: list[str]) -> ShellResult:
        if not args:
            return _out(tint("yellow", "usage: cat <file>   (try: cat about.txt)"))
        lines: list[str] = []
        for arg in args:
            path = self.vfs.resolve(arg, self.cwd)
            text = self.vfs.read(path)
            if text is not None:
                lines += [safe(line) for line in text.splitlines()]
            elif self.vfs.is_dir(path):
                lines.append(tint("danger", f"cat: {arg}: is a directory"))
            else:
                lines.append(tint("danger", f"cat: {arg}: no such file in this sector"))
        return _out(*lines)

    def _echo(self, args: list[str]) -> ShellResult:
        return _out(safe(" ".join(args)))

    def _projects(self, args: list[str]) -> ShellResult:
        lines = [tint("magenta", "MISSION DOSSIERS", "bold")]
        for index, project in enumerate(self.profile.projects, start=1):
            lines.append(
                f"  {tint('yellow', f'[{index:02d}]')} {tint('dim', str(project.year))}  "
                f"{tint('cyan', project.title, 'bold')}"
            )
            lines.append(tint("dim", f"       cat ~/projects/{project.slug}.md"))
        return _out(*lines)

    def _skills(self, args: list[str]) -> ShellResult:
        lines: list[str] = [tint("dim", "relative proficiency (stylized)")]
        width = max(len(s.name) for cat in self.profile.skills for s in cat.skills)
        for category in self.profile.skills:
            lines.append(tint("magenta", category.name.upper(), "bold"))
            lines += [
                f"  {safe(skill.name.ljust(width))}  {_bar(skill.level)}"
                for skill in category.skills
            ]
        lines.append(tint("magenta", "SPOKEN", "bold"))
        lines += [
            f"  {safe(lang.name.ljust(width))}  {_bar(lang.bar)} {tint('yellow', lang.level)}"
            for lang in self.profile.languages
        ]
        return _out(*lines)

    def _contact(self, args: list[str]) -> ShellResult:
        contact = self.profile.contact
        lines = [
            f"{tint('dim', 'email   ')} {tint('cyan', contact.email)}",
            f"{tint('dim', 'github  ')} {tint('cyan', contact.github_url)}",
            f"{tint('dim', 'location')} {safe(contact.location)}",
        ]
        if contact.phone_sealed:
            lines.append(
                f"{tint('dim', 'phone   ')} {tint('magenta', '▓▒░ sealed')} "
                f"{tint('dim', '(run: decrypt phone)')}"
            )
        return _out(*lines)

    def _decrypt(self, args: list[str]) -> ShellResult:
        phone = self.profile.contact.phone
        if not args or args[0].lower() != "phone":
            return _out(tint("yellow", "usage: decrypt phone"))
        if phone is None:
            return _out(tint("dim", "decrypt: no sealed phone number on this node."))
        return ShellResult(
            (
                tint("dim", "▓▒░ reading sealed field contact.phone"),
                tint("dim", "▓▒░ applying keystream"),
                tint("dim", "▓▒░ checksum ok"),
                f"{tint('dim', 'phone')} {tint('green', phone, 'bold')}",
            ),
            pace=1,
        )

    def _neofetch(self, args: list[str]) -> ShellResult:
        profile = self.profile
        elapsed = int(self._clock() - self._started)
        hours, rest = divmod(elapsed, 3600)
        minutes, seconds = divmod(rest, 60)
        title = f"{self.user}@{self.lore.hostname}"
        info = [
            ("", tint("green", title, "bold")),
            ("", tint("dim", "-" * len(title))),
            ("OS", f"{self.lore.kernel} (fictional)"),
            ("Host", f"{profile.identity.name} ({profile.identity.handle})"),
            ("Role", profile.identity.title),
            ("Location", profile.identity.location),
            ("Degree", profile.education[0].degree),
            ("Projects", str(len(profile.projects))),
            ("Awards", str(len(profile.awards))),
            ("Stack", ", ".join(skill.name for skill in profile.skills[0].skills)),
            ("Spoken", ", ".join(f"{lang.name} ({lang.level})" for lang in profile.languages)),
            ("Shell", self.lore.shell_name),
            ("Theme", self.current_theme),
            ("Uptime", f"{hours}h {minutes:02d}m {seconds:02d}s (this session)"),
            ("", "".join(f"[$neon-{c}]███[/]" for c in ("cyan", "magenta", "yellow", "green"))),
        ]
        lines = []
        logo_width = max(len(row) for row in NEOFETCH_LOGO)
        for index, (label, value) in enumerate(info):
            logo = NEOFETCH_LOGO[index] if index < len(NEOFETCH_LOGO) else ""
            left = tint("cyan", logo.ljust(logo_width), "bold")
            if label:
                if len(value) > NEOFETCH_VALUE_WIDTH:
                    value = value[: NEOFETCH_VALUE_WIDTH - 1] + "…"
                value = f"{tint('magenta', label + ':', 'bold')} {safe(value)}"
            lines.append(f"{left}  {value}")
        return _out(*lines)

    def _grep(self, args: list[str]) -> ShellResult:
        if not args:
            return _out(tint("yellow", "usage: grep <text>   (try: grep python)"))
        needle = " ".join(args)
        lowered = needle.lower()
        hits: list[str] = []
        for path, text in self.vfs.files():
            for line in text.splitlines():
                index = line.lower().find(lowered)
                if index < 0:
                    continue
                before, found, after = (
                    line[:index],
                    line[index : index + len(needle)],
                    line[index + len(needle) :],
                )
                hits.append(
                    f"{tint('magenta', path)}{tint('dim', ':')} "
                    f"{safe(before)}{tint('yellow', found, 'bold reverse')}{safe(after)}"
                )
        if not hits:
            return _out(tint("dim", f"grep: no match for '{needle}'"))
        extra = len(hits) - MAX_GREP_MATCHES
        lines = hits[:MAX_GREP_MATCHES]
        if extra > 0:
            lines.append(tint("dim", f"... {extra} more match(es)"))
        return _out(*lines)

    def _open(self, args: list[str]) -> ShellResult:
        projects = self.profile.projects
        if not args:
            return _out(tint("yellow", f"usage: open <1-{len(projects)}|slug>   (try: open 1)"))
        choice = args[0].lower()
        for index, project in enumerate(projects, start=1):
            if choice in (str(index), f"{index:02d}", project.slug):
                return _out(
                    tint("green", f"decrypting dossier #{index:02d}: {project.title}"),
                    action="open_project",
                    argument=project.slug,
                )
        return _out(tint("danger", f"open: no dossier '{args[0]}'. Run 'projects' to list."))

    def _timeline(self, args: list[str]) -> ShellResult:
        lines = [tint("magenta", "CAREER LOG // newest first", "bold")]
        entries = build_timeline(self.profile)
        width = max(len(entry.when) for entry in entries)
        for entry in entries:
            color = KIND_COLOR[entry.kind]
            lines.append(
                f"  {tint('dim', entry.when.rjust(width))} {tint(color, KIND_GLYPH[entry.kind])} "
                f"{tint(color, entry.title, 'bold')} {tint('dim', '· ' + entry.detail)}"
            )
        return _out(*lines)

    def _fortune(self, args: list[str]) -> ShellResult:
        return _out(tint("cyan", f"“{self._rng.choice(self.lore.shell_fortunes)}”"))

    def _hack(self, args: list[str]) -> ShellResult:
        colors = {"[*]": "cyan", "[!]": "danger", "[+]": "green"}
        lines = [tint(colors.get(line.strip()[:3], "dim"), line) for line in self.lore.shell_hack]
        return ShellResult(tuple(lines), pace=1)

    def _history(self, args: list[str]) -> ShellResult:
        return _out(
            *(
                f"{tint('dim', f'{index:>4}')}  {safe(entry)}"
                for index, entry in enumerate(self.history, start=1)
            )
        )

    def _classified(self, args: list[str]) -> ShellResult:
        file_id = self.lore.overwatch.file_id
        return _out(
            tint("danger", f"opening restricted file {file_id}... access will be logged.", "bold"),
            action="classified",
        )

    def _matrix(self, args: list[str]) -> ShellResult:
        return _out(
            tint("green", "Entering the rain... press any key to come back."), action="matrix"
        )

    def _theme(self, args: list[str]) -> ShellResult:
        if not args:
            listing = "  ".join(
                tint("cyan", name, "bold") if name == self.current_theme else safe(name)
                for name in self.themes
            )
            return _out(listing, tint("dim", "usage: theme <name>"))
        name = args[0].lower()
        if name not in self.themes:
            return _out(tint("danger", f"theme: unknown theme '{args[0]}'. Run 'theme' to list."))
        self.current_theme = name
        return _out(tint("green", f"palette swapped to {name}."), action="theme", argument=name)

    def _clear(self, args: list[str]) -> ShellResult:
        return _out(action="clear")

    def _exit(self, args: list[str]) -> ShellResult:
        return _out(tint("magenta", "Jacking out... stay frosty, runner."), action="exit")
