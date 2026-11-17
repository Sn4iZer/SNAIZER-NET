"""Load and validate the portfolio content files.

``profile.yaml`` holds every real fact shown by the app; ``lore.yaml`` holds
clearly fictional flavor text. Both are parsed into frozen dataclasses so the
UI never touches raw YAML.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml

PERIOD_RE = re.compile(r"^\d{4}(-(\d{4}|present))?$")
T = TypeVar("T")


class ContentError(Exception):
    """Raised when a content file is missing, unreadable or invalid."""


@dataclass(frozen=True)
class Identity:
    """Who the portfolio is about."""

    name: str
    handle: str
    title: str
    location: str
    bio: str


@dataclass(frozen=True)
class Contact:
    """Public contact channels."""

    email: str
    github: str
    location: str

    @property
    def github_url(self) -> str:
        """Full GitHub profile URL."""
        return f"https://github.com/{self.github}"

    @property
    def mailto_url(self) -> str:
        """``mailto:`` URL for the email address."""
        return f"mailto:{self.email}"


@dataclass(frozen=True)
class Highlight:
    """A headline number shown on the profile screen."""

    label: str
    value: str


@dataclass(frozen=True)
class Education:
    """A degree entry."""

    degree: str
    institution: str
    location: str
    period: str


@dataclass(frozen=True)
class Skill:
    """A single skill with a stylized relative proficiency (0-100)."""

    name: str
    level: int


@dataclass(frozen=True)
class SkillCategory:
    """A named group of skills."""

    name: str
    skills: tuple[Skill, ...]


@dataclass(frozen=True)
class Language:
    """A spoken language; ``level`` is shown verbatim, ``bar`` drives the visual."""

    name: str
    level: str
    bar: int


@dataclass(frozen=True)
class Project:
    """A project dossier."""

    slug: str
    title: str
    kind: str
    year: int
    summary: str
    bullets: tuple[str, ...]
    tags: tuple[str, ...]


@dataclass(frozen=True)
class Award:
    """A competition result."""

    place: str
    title: str
    organizer: str
    year: int
    description: str


@dataclass(frozen=True)
class Experience:
    """A work or entrepreneurship entry."""

    title: str
    organization: str
    period: str
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class Profile:
    """All real portfolio data."""

    identity: Identity
    contact: Contact
    highlights: tuple[Highlight, ...]
    education: tuple[Education, ...]
    skills: tuple[SkillCategory, ...]
    languages: tuple[Language, ...]
    projects: tuple[Project, ...]
    awards: tuple[Award, ...]
    experience: tuple[Experience, ...]


@dataclass(frozen=True)
class BootLine:
    """One fictional line of the boot log."""

    status: str
    text: str


@dataclass(frozen=True)
class Lore:
    """Fictional flavor text."""

    hostname: str
    kernel: str
    shell_name: str
    boot_lines: tuple[BootLine, ...]
    login_hint: str
    login_denied_empty: str
    login_trace_abort: str
    shell_unknown: tuple[str, ...]
    shell_forbidden: tuple[str, ...]
    shell_motd: str
    blackice_title: str
    blackice_body: tuple[str, ...]


def default_content_dir() -> Path:
    """Return the ``content/`` directory shipped next to the package."""
    return Path(__file__).resolve().parent.parent / "content"


def _read_yaml(path: Path) -> Mapping[str, Any]:
    """Read a YAML file and make sure its top level is a mapping."""
    if not path.is_file():
        raise ContentError(f"{path}: file not found")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ContentError(f"{path}: invalid YAML ({error})") from error
    except (OSError, UnicodeDecodeError) as error:
        raise ContentError(f"{path}: cannot read file ({error})") from error
    if not isinstance(data, Mapping):
        raise ContentError(f"{path}: top level must be a mapping of sections")
    return data


def _get(data: Any, key: str, kind: type[T], where: str) -> T:
    """Fetch ``data[key]`` and check its type, raising a precise ContentError."""
    if not isinstance(data, Mapping):
        raise ContentError(f"{where}: expected a mapping")
    if key not in data or data[key] is None:
        raise ContentError(f"{where}.{key}: missing required field")
    value = data[key]
    if kind is int and isinstance(value, bool):
        raise ContentError(f"{where}.{key}: expected int, got bool")
    if kind is str and isinstance(value, int | float):
        value = str(value)
    if not isinstance(value, kind):
        raise ContentError(f"{where}.{key}: expected {kind.__name__}, got {type(value).__name__}")
    if kind is str:
        value = value.strip()  # type: ignore[union-attr]
        if not value:
            raise ContentError(f"{where}.{key}: must not be empty")
    return value  # type: ignore[return-value]


def _str_list(data: Any, key: str, where: str) -> tuple[str, ...]:
    """Fetch a non-empty list of non-empty strings."""
    items = _get(data, key, list, where)
    if not items:
        raise ContentError(f"{where}.{key}: must not be empty")
    result: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, str | int | float) or not str(item).strip():
            raise ContentError(f"{where}.{key}[{index}]: expected a non-empty string")
        result.append(str(item).strip())
    return tuple(result)


def _records(data: Any, key: str, where: str) -> list[tuple[str, Any]]:
    """Fetch a non-empty list of mappings, paired with their error location."""
    items = _get(data, key, list, where)
    if not items:
        raise ContentError(f"{where}.{key}: must not be empty")
    return [(f"{where}.{key}[{index}]", item) for index, item in enumerate(items)]


def _level(data: Any, key: str, where: str) -> int:
    """Fetch an integer in the 0-100 range."""
    value = _get(data, key, int, where)
    if not 0 <= value <= 100:
        raise ContentError(f"{where}.{key}: must be between 0 and 100")
    return value


def _year(data: Any, key: str, where: str) -> int:
    """Fetch a plausible four-digit year."""
    value = _get(data, key, int, where)
    if not 1900 <= value <= 2100:
        raise ContentError(f"{where}.{key}: {value} is not a valid year")
    return value


def _period(data: Any, key: str, where: str) -> str:
    """Fetch a ``YYYY`` / ``YYYY-YYYY`` / ``YYYY-present`` period."""
    value = _get(data, key, str, where)
    if not PERIOD_RE.match(value):
        raise ContentError(f"{where}.{key}: '{value}' must look like 2023 or 2023-2025")
    return value


def parse_profile(data: Mapping[str, Any], source: str = "profile.yaml") -> Profile:
    """Validate a raw mapping and build a :class:`Profile`."""
    ident = _get(data, "identity", Mapping, source)
    where = f"{source}:identity"
    identity = Identity(
        name=_get(ident, "name", str, where),
        handle=_get(ident, "handle", str, where),
        title=_get(ident, "title", str, where),
        location=_get(ident, "location", str, where),
        bio=" ".join(_get(ident, "bio", str, where).split()),
    )

    cont = _get(data, "contact", Mapping, source)
    where = f"{source}:contact"
    email = _get(cont, "email", str, where)
    if "@" not in email:
        raise ContentError(f"{where}.email: '{email}' is not an email address")
    contact = Contact(
        email=email,
        github=_get(cont, "github", str, where),
        location=_get(cont, "location", str, where),
    )

    highlights = tuple(
        Highlight(label=_get(item, "label", str, at), value=_get(item, "value", str, at))
        for at, item in (_records(data, "highlights", source) if data.get("highlights") else [])
    )

    education = tuple(
        Education(
            degree=_get(item, "degree", str, at),
            institution=_get(item, "institution", str, at),
            location=_get(item, "location", str, at),
            period=_period(item, "period", at),
        )
        for at, item in _records(data, "education", source)
    )

    skills = tuple(
        SkillCategory(
            name=_get(item, "category", str, at),
            skills=tuple(
                Skill(name=_get(skill, "name", str, sat), level=_level(skill, "level", sat))
                for sat, skill in _records(item, "items", at)
            ),
        )
        for at, item in _records(data, "skills", source)
    )

    languages = tuple(
        Language(
            name=_get(item, "name", str, at),
            level=_get(item, "level", str, at),
            bar=_level(item, "bar", at),
        )
        for at, item in _records(data, "languages", source)
    )

    projects = tuple(
        Project(
            slug=_get(item, "slug", str, at),
            title=_get(item, "title", str, at),
            kind=_get(item, "kind", str, at),
            year=_year(item, "year", at),
            summary=" ".join(_get(item, "summary", str, at).split()),
            bullets=_str_list(item, "bullets", at),
            tags=_str_list(item, "tags", at),
        )
        for at, item in _records(data, "projects", source)
    )
    slugs = [project.slug for project in projects]
    for slug in slugs:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            raise ContentError(f"{source}:projects: slug '{slug}' must be lowercase-kebab-case")
        if slugs.count(slug) > 1:
            raise ContentError(f"{source}:projects: duplicate slug '{slug}'")

    awards = tuple(
        Award(
            place=_get(item, "place", str, at),
            title=_get(item, "title", str, at),
            organizer=_get(item, "organizer", str, at),
            year=_year(item, "year", at),
            description=_get(item, "description", str, at),
        )
        for at, item in _records(data, "awards", source)
    )

    experience = tuple(
        Experience(
            title=_get(item, "title", str, at),
            organization=_get(item, "organization", str, at),
            period=_period(item, "period", at),
            bullets=_str_list(item, "bullets", at),
        )
        for at, item in _records(data, "experience", source)
    )

    return Profile(
        identity=identity,
        contact=contact,
        highlights=highlights,
        education=education,
        skills=skills,
        languages=languages,
        projects=projects,
        awards=awards,
        experience=experience,
    )


def parse_lore(data: Mapping[str, Any], source: str = "lore.yaml") -> Lore:
    """Validate a raw mapping and build a :class:`Lore`."""
    node = _get(data, "node", Mapping, source)
    login = _get(data, "login", Mapping, source)
    shell = _get(data, "shell", Mapping, source)
    blackice = _get(data, "blackice", Mapping, source)
    body = _get(blackice, "body", list, f"{source}:blackice")
    return Lore(
        hostname=_get(node, "hostname", str, f"{source}:node"),
        kernel=_get(node, "kernel", str, f"{source}:node"),
        shell_name=_get(node, "shell", str, f"{source}:node"),
        boot_lines=tuple(
            BootLine(status=_get(item, "status", str, at).upper(), text=_get(item, "text", str, at))
            for at, item in _records(data, "boot_lines", source)
        ),
        login_hint=_get(login, "hint", str, f"{source}:login"),
        login_denied_empty=_get(login, "denied_empty", str, f"{source}:login"),
        login_trace_abort=_get(login, "trace_abort", str, f"{source}:login"),
        shell_unknown=_str_list(shell, "unknown", f"{source}:shell"),
        shell_forbidden=_str_list(shell, "forbidden", f"{source}:shell"),
        shell_motd=_get(shell, "motd", str, f"{source}:shell"),
        blackice_title=_get(blackice, "title", str, f"{source}:blackice"),
        blackice_body=tuple("" if line is None else str(line) for line in body),
    )


def load_profile(path: Path | None = None) -> Profile:
    """Load and validate ``profile.yaml``."""
    path = path or default_content_dir() / "profile.yaml"
    return parse_profile(_read_yaml(path), source=str(path))


def load_lore(path: Path | None = None) -> Lore:
    """Load and validate ``lore.yaml``."""
    path = path or default_content_dir() / "lore.yaml"
    return parse_lore(_read_yaml(path), source=str(path))
