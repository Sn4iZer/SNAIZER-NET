"""The list of main-screen sections, shared by navigation widgets and screens."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionSpec:
    """A navigable section of the main screen."""

    key: str
    id: str
    title: str
    short: str
    blurb: str
    """One plain sentence under the heading: what this is and how to use it."""
    admin_only: bool = False

    @property
    def path(self) -> str:
        """The section as a directory on the node, e.g. ``~/projects``."""
        return f"~/{self.id}"


SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("1", "profile", "profile", "prof", "Who I am and what I'm working on now."),
    SectionSpec("2", "education", "education", "edu", "Degrees, newest first."),
    SectionSpec("3", "skills", "skills", "skl", "Tools and languages I work with."),
    SectionSpec(
        "4", "projects", "projects", "proj", "Open a case file to read it; f filters by tag."
    ),
    SectionSpec("5", "awards", "awards", "awd", "Competition results."),
    SectionSpec("6", "experience", "experience", "exp", "Jobs and ventures, newest first."),
    SectionSpec(
        "7",
        "contact",
        "contact",
        "ctc",
        "Email and GitHub are open; decrypt the phone (d or the button).",
    ),
    SectionSpec(
        "8", "terminal", "terminal", "term", "A sandboxed shell over this portfolio. Try help."
    ),
    SectionSpec("9", "timeline", "timeline", "time", "Everything on one axis, newest first."),
    SectionSpec(
        "0",
        "blackice",
        "black-ice",
        "ice",
        "Fiction, for whoever typed the right name at the gate.",
        admin_only=True,
    ),
)


def visible_sections(admin: bool) -> tuple[SectionSpec, ...]:
    """Sections available to this runner (BLACK-ICE needs the ADMIN badge)."""
    return tuple(spec for spec in SECTIONS if admin or not spec.admin_only)
