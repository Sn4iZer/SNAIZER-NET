"""The classified-file walkthrough as data: segments, timing and styled text.

Every *fact* comes from :class:`~snaizer_net.content.Profile`; only the framing
(alarm words, machine narration, ending) comes from ``lore.yaml``. Nothing here
touches the UI, so the whole "video" can be tested frame by frame.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from snaizer_net.content import OVERWATCH_SCENES, Lore, Profile
from snaizer_net.markup import tint
from snaizer_net.timeline import period_label

Kind = Literal["breach", "online", "scene", "ending"]
Span = tuple[str, str, str]
"""``(text, color, style)``; color is a ``$neon-*`` name or :data:`SECRET`."""
Cell = Span
"""A single character with its color and style."""

SECRET = "secret"
"""Color marker for the sealed phone number; rendered by the decode effect."""

DURATIONS: dict[str, float] = {
    "breach": 4.0,
    "online": 3.0,
    "identity": 6.0,
    "education": 6.0,
    "skills": 7.0,
    "projects": 9.0,
    "awards": 5.0,
    "experience": 7.0,
    "contact": 6.0,
    "ending": 8.0,
}
"""Seconds per segment (about one minute in total)."""

TITLES: dict[str, str] = {
    "identity": "IDENTITY",
    "education": "EDUCATION",
    "skills": "CAPABILITIES",
    "projects": "OPERATIONS",
    "awards": "RECOGNITION",
    "experience": "FIELD ACTIVITY",
    "contact": "CHANNELS",
}

LABEL_WIDTH = 10
BAR_WIDTH = 16


@dataclass(frozen=True)
class Segment:
    """One stretch of the walkthrough."""

    id: str
    kind: Kind
    duration: float
    title: str = ""
    narration: tuple[str, ...] = ()
    facts: tuple[tuple[Span, ...], ...] = ()
    secret: str = ""
    """Plain text behind :data:`SECRET` spans (the phone number), if any."""


def span(text: str, color: str = "text", style: str = "") -> Span:
    """Build a styled span."""
    return (text, color, style)


def fill(template: str, values: dict[str, str]) -> str:
    """``str.format`` that leaves unknown or malformed placeholders untouched."""

    class _Keep(dict[str, str]):
        def __missing__(self, key: str) -> str:
            return "{" + key + "}"

    try:
        return template.format_map(_Keep(values))
    except (ValueError, IndexError, AttributeError):
        return template


def _label(text: str) -> Span:
    return span(text.ljust(LABEL_WIDTH), "dim")


def _bar(level: float) -> tuple[Span, ...]:
    filled = round(level / 100 * BAR_WIDTH)
    head = "╸" if 0 < filled < BAR_WIDTH else ""
    body = max(0, filled - len(head))
    return (
        span("━" * body, "cyan"),
        span(head, "magenta", "bold"),
        span("─" * (BAR_WIDTH - body - len(head)), "dim"),
    )


def _facts(scene: str, profile: Profile) -> tuple[tuple[tuple[Span, ...], ...], str]:
    """Fact lines for ``scene`` and the secret behind any :data:`SECRET` span."""
    ident, contact = profile.identity, profile.contact
    lines: list[tuple[Span, ...]] = []
    secret = ""
    if scene == "identity":
        lines = [
            (_label("name"), span(ident.name, "text", "bold")),
            (_label("alias"), span(ident.handle, "magenta", "bold")),
            (_label("role"), span(ident.title)),
            (_label("location"), span(ident.location)),
        ]
    elif scene == "education":
        for edu in profile.education:
            lines.append(
                (
                    span(period_label(edu.period).ljust(14), "yellow"),
                    span(edu.degree, "text", "bold"),
                )
            )
            lines.append((span(" " * 14), span(f"{edu.institution}, {edu.location}", "dim")))
    elif scene == "skills":
        for category in profile.skills:
            average = mean(skill.level for skill in category.skills)
            lines.append((span(category.name.ljust(14), "cyan", "bold"), *_bar(average)))
            names = ", ".join(skill.name for skill in category.skills)
            lines.append((span(" " * 14), span(names, "dim")))
        spoken = ", ".join(f"{lang.name} ({lang.level})" for lang in profile.languages)
        lines.append((span("Spoken".ljust(14), "cyan", "bold"), span(spoken)))
    elif scene == "projects":
        for index, project in enumerate(profile.projects, start=1):
            lines.append(
                (
                    span(f"OP-{index:02d} ", "yellow"),
                    span(project.title, "text", "bold"),
                    span(f"  {project.year}", "yellow"),
                )
            )
            lines.append((span(" " * 7), span(project.kind, "dim")))
    elif scene == "awards":
        for award in profile.awards:
            lines.append(
                (
                    span(f"{award.place}  ", "yellow", "bold"),
                    span(award.title, "text", "bold"),
                    span(f"  {award.year}", "yellow"),
                )
            )
            lines.append((span(" " * 2), span(f"{award.organizer}: {award.description}", "dim")))
    elif scene == "experience":
        for exp in profile.experience:
            lines.append(
                (
                    span(period_label(exp.period).ljust(18), "yellow"),
                    span(exp.title, "text", "bold"),
                )
            )
            lines.append((span(" " * 18), span(exp.organization, "dim")))
    elif scene == "contact":
        lines = [
            (_label("email"), span(contact.email, "cyan", "bold")),
            (_label("github"), span(contact.github_url, "cyan")),
            (_label("location"), span(contact.location)),
        ]
        if contact.phone:
            secret = contact.phone
            lines.append((_label("phone"), span("▓" * len(secret), SECRET)))
    return tuple(lines), secret


def build_segments(profile: Profile, lore: Lore) -> list[Segment]:
    """The whole walkthrough, in playback order."""
    ow = lore.overwatch
    values = {
        "name": profile.identity.name,
        "handle": profile.identity.handle,
        "projects": str(len(profile.projects)),
        "awards": str(len(profile.awards)),
        "system": ow.system,
        "file_id": ow.file_id,
    }
    segments = [
        Segment("breach", "breach", DURATIONS["breach"]),
        Segment(
            "online",
            "online",
            DURATIONS["online"],
            narration=tuple(fill(line, values) for line in ow.online),
        ),
    ]
    for scene in OVERWATCH_SCENES:
        facts, secret = _facts(scene, profile)
        segments.append(
            Segment(
                scene,
                "scene",
                DURATIONS[scene],
                title=TITLES[scene],
                narration=tuple(fill(line, values) for line in ow.narration[scene]),
                facts=facts,
                secret=secret,
            )
        )
    segments.append(
        Segment(
            "ending",
            "ending",
            DURATIONS["ending"],
            narration=tuple(fill(line, values) for line in ow.ending),
        )
    )
    return segments


class Timeline:
    """Maps elapsed seconds onto segments."""

    def __init__(self, segments: Sequence[Segment]) -> None:
        self.segments = list(segments)
        self.starts: list[float] = []
        total = 0.0
        for segment in self.segments:
            self.starts.append(total)
            total += segment.duration
        self.total = total
        self.scenes = [i for i, s in enumerate(self.segments) if s.kind == "scene"]

    def locate(self, elapsed: float) -> tuple[int, float]:
        """``(segment index, seconds into that segment)`` for ``elapsed``."""
        elapsed = max(0.0, min(elapsed, self.total))
        for index in range(len(self.segments) - 1, -1, -1):
            if elapsed >= self.starts[index]:
                local = elapsed - self.starts[index]
                return index, min(local, self.segments[index].duration)
        return 0, 0.0

    def scene_number(self, index: int) -> int:
        """1-based scene number for a segment index (0 if it is not a scene)."""
        return self.scenes.index(index) + 1 if index in self.scenes else 0


# -- styled-cell helpers ------------------------------------------------------


def to_cells(line: Sequence[Span]) -> list[Cell]:
    """Explode spans into per-character cells."""
    return [(char, color, style) for text, color, style in line for char in text]


def wrap_cells(cells: list[Cell], width: int, indent: int = 0) -> list[list[Cell]]:
    """Greedy word wrap that keeps each character's style.

    Continuation lines start with ``indent`` spaces (a hanging indent), so
    wrapped values stay in their column.
    """
    width = max(1, width)
    indent = min(indent, width // 2)
    pad: list[Cell] = [(" ", "text", "")] * indent
    lines: list[list[Cell]] = []
    floor = 0  # cuts must land after this index (past the indent on continuation lines)
    while len(cells) > width:
        # Break at the last space that leaves real text on this line; a word too
        # long for the line is hard-cut, so every pass makes progress.
        cut = next((i for i in range(width, floor, -1) if cells[i][0] == " "), width)
        lines.append(cells[:cut])
        cells = cells[cut:]
        while cells and cells[0][0] == " ":
            cells = cells[1:]
        cells = pad + cells
        floor = indent
    lines.append(cells)
    return lines


STACK_INDENT = 2
"""Indent of a value moved under its label by ``layout(stack=True)``."""


def layout(facts: Sequence[Sequence[Span]], width: int, stack: bool = False) -> list[list[Cell]]:
    """Wrap every fact line to ``width``, hanging under its first column.

    With ``stack`` (phones), a value that won't fit beside its label column
    moves under it: ``email`` / ``  mohammedtchichi03@gmail.com``. Rows whose
    first column is blank padding simply lose it.
    """
    rows: list[list[Cell]] = []
    for line in facts:
        indent = len(line[0][0]) if len(line) > 1 else 0
        rest = sum(len(text) for text, _, _ in line[1:])
        if stack and indent and rest > width - indent:
            label = line[0][0].rstrip()
            if label:
                rows.append(to_cells([(label, *line[0][1:])]))
            pad: Span = (" " * STACK_INDENT, "text", "")
            rows += wrap_cells(to_cells([pad, *line[1:]]), width, STACK_INDENT)
        else:
            rows += wrap_cells(to_cells(line), width, indent)
    return rows


def reveal(lines: list[list[Cell]], count: int) -> list[list[Cell]]:
    """The first ``count`` cells across all lines (typewriter effect)."""
    shown: list[list[Cell]] = []
    for line in lines:
        if count <= 0:
            break
        shown.append(line[:count])
        count -= len(line)
    return shown


def cells_markup(cells: list[Cell], secret: Callable[[int], str] | None = None) -> str:
    """Markup for a row of cells; :data:`SECRET` runs are drawn by ``secret(n)``."""
    out: list[str] = []
    index = 0
    while index < len(cells):
        _, color, style = cells[index]
        end = index
        while end < len(cells) and cells[end][1:] == (color, style):
            end += 1
        text = "".join(cell[0] for cell in cells[index:end])
        if color == SECRET:
            out.append(secret(len(text)) if secret else tint("dim", text))
        else:
            out.append(tint(color, text, style))
        index = end
    return "".join(out)
