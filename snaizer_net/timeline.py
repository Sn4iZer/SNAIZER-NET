"""A single chronological view over education, experience, projects and awards."""

from dataclasses import dataclass
from typing import Literal

from snaizer_net.content import MONTHS, Period, Profile, parse_period

Kind = Literal["education", "experience", "project", "award"]
# Same-year tie-break: degrees first (they frame the year), then awards, jobs, projects.
KIND_RANK: dict[Kind, int] = {"education": 4, "award": 3, "experience": 2, "project": 1}
MONTH_NAMES = {index: name.capitalize() for name, index in MONTHS.items()}
KIND_COLOR: dict[Kind, str] = {
    "education": "cyan",
    "experience": "green",
    "project": "magenta",
    "award": "yellow",
}
KIND_GLYPH: dict[Kind, str] = {"education": "◆", "experience": "▣", "project": "◈", "award": "★"}


@dataclass(frozen=True)
class TimelineEntry:
    """One dated event."""

    when: str
    kind: Kind
    title: str
    detail: str
    sort_key: tuple[int, int, int]


def _point(year: int, month: int) -> str:
    return f"{MONTH_NAMES[month]} {year}" if month else str(year)


def format_period(period: Period) -> str:
    """Compact, typographic label.

    ``Jun 2026 - Jul 2026`` -> ``Jun–Jul 2026``; ``2023-2025`` -> ``2023–2025``;
    ``2026-present`` -> ``2026–present``; ``2024`` -> ``2024``.
    """
    (start_year, start_month), end = period.start, period.end
    if end is None:
        return f"{_point(start_year, start_month)}–present"
    if end == period.start:
        return _point(start_year, start_month)
    if start_month and end[1] and start_year == end[0]:
        return f"{MONTH_NAMES[start_month]}–{MONTH_NAMES[end[1]]} {start_year}"
    return f"{_point(start_year, start_month)}–{_point(*end)}"


def period_label(text: str) -> str:
    """:func:`format_period` for a raw period string (unchanged if unparsable)."""
    period = parse_period(text)
    return format_period(period) if period else text


def build_timeline(profile: Profile) -> list[TimelineEntry]:
    """All dated events, newest first."""
    entries: list[TimelineEntry] = []

    def add(when: str, kind: Kind, title: str, detail: str, start: tuple[int, int]) -> None:
        entries.append(TimelineEntry(when, kind, title, detail, (*start, KIND_RANK[kind])))

    for edu in profile.education:
        period = parse_period(edu.period)
        if period:
            where = f"{edu.institution}, {edu.location}"
            add(format_period(period), "education", edu.degree, where, period.start)
    for exp in profile.experience:
        period = parse_period(exp.period)
        if period:
            add(format_period(period), "experience", exp.title, exp.organization, period.start)
    for project in profile.projects:
        add(str(project.year), "project", project.title, project.kind, (project.year, 0))
    for award in profile.awards:
        add(
            str(award.year),
            "award",
            f"{award.place}: {award.title}",
            award.organizer,
            (award.year, 0),
        )
    return sorted(entries, key=lambda entry: entry.sort_key, reverse=True)
