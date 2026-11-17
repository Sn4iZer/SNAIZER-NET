"""The list of main-screen sections, shared by navigation widgets and screens."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionSpec:
    """A navigable section of the main screen."""

    key: str
    id: str
    title: str
    short: str
    admin_only: bool = False


SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("1", "profile", "PROFILE", "PROF"),
    SectionSpec("2", "education", "EDUCATION", "EDU"),
    SectionSpec("3", "skills", "SKILLS", "SKL"),
    SectionSpec("4", "projects", "PROJECTS", "PROJ"),
    SectionSpec("5", "awards", "AWARDS", "AWD"),
    SectionSpec("6", "experience", "EXPERIENCE", "EXP"),
    SectionSpec("7", "contact", "CONTACT", "CTC"),
    SectionSpec("8", "terminal", "TERMINAL", "TERM"),
    SectionSpec("9", "timeline", "TIMELINE", "TIME"),
    SectionSpec("0", "blackice", "BLACK-ICE", "ICE", admin_only=True),
)


def visible_sections(admin: bool) -> tuple[SectionSpec, ...]:
    """Sections available to this runner (BLACK-ICE needs the ADMIN badge)."""
    return tuple(spec for spec in SECTIONS if admin or not spec.admin_only)
