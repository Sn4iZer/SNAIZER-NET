"""A tiny read-only, in-memory filesystem for the fake shell.

Paths are plain strings manipulated with :mod:`posixpath` (pure string
functions). The real filesystem is never touched.
"""

import posixpath
from collections.abc import Mapping

from snaizer_net.content import Lore, Profile

HOME = "/home/runner"


class VirtualFS:
    """Files are a ``{absolute_path: text}`` mapping; directories are implied."""

    def __init__(self, files: Mapping[str, str]) -> None:
        self._files = dict(files)
        self._dirs = {"/"}
        for path in self._files:
            parent = posixpath.dirname(path)
            while parent not in self._dirs:
                self._dirs.add(parent)
                parent = posixpath.dirname(parent)

    @staticmethod
    def resolve(path: str, cwd: str) -> str:
        """Turn ``path`` (relative, absolute or ``~``-based) into a clean absolute path."""
        if path == "~" or path.startswith("~/"):
            path = HOME + path[1:]
        joined = path if path.startswith("/") else posixpath.join(cwd, path)
        normalized = posixpath.normpath(joined)
        return "/" + normalized.lstrip("/")

    def is_dir(self, path: str) -> bool:
        """True if ``path`` is a directory."""
        return path in self._dirs

    def read(self, path: str) -> str | None:
        """Contents of a file, or ``None`` if it does not exist."""
        return self._files.get(path)

    def listdir(self, path: str) -> list[str]:
        """Sorted entry names in ``path``; directories end with ``/``."""
        prefix = path.rstrip("/") + "/"
        names: set[str] = set()
        for candidate in (*self._dirs, *self._files):
            if candidate != path and candidate.startswith(prefix):
                head = candidate[len(prefix) :].split("/", 1)[0]
                is_dir = self.is_dir(prefix + head)
                names.add(head + ("/" if is_dir else ""))
        return sorted(names, key=lambda name: (not name.endswith("/"), name))


def build_vfs(profile: Profile, lore: Lore, admin: bool = False) -> VirtualFS:
    """Populate the virtual filesystem from the portfolio content."""
    ident, contact = profile.identity, profile.contact
    files: dict[str, str] = {
        f"{HOME}/README.txt": "\n".join(
            [
                lore.shell_motd,
                "",
                "Try: ls, cat about.txt, projects, skills, neofetch, matrix, help",
            ]
        ),
        f"{HOME}/about.txt": "\n".join(
            [
                f"{ident.name} ({ident.handle})",
                ident.title,
                ident.location,
                "",
                ident.bio,
            ]
        ),
        f"{HOME}/contact.txt": "\n".join(
            [
                f"email:    {contact.email}",
                f"github:   {contact.github_url}",
                f"location: {contact.location}",
            ]
        ),
        f"{HOME}/education.txt": "\n".join(
            f"{edu.period}  {edu.degree}, {edu.institution}, {edu.location}"
            for edu in profile.education
        ),
        f"{HOME}/skills.txt": "\n".join(
            [
                *(
                    f"{cat.name}: " + ", ".join(skill.name for skill in cat.skills)
                    for cat in profile.skills
                ),
                "Spoken: " + ", ".join(f"{lang.name} ({lang.level})" for lang in profile.languages),
            ]
        ),
        f"{HOME}/awards.txt": "\n".join(
            f"{award.year}  {award.place}: {award.title} ({award.organizer})\n"
            f"      {award.description}"
            for award in profile.awards
        ),
        f"{HOME}/experience.txt": "\n".join(
            f"{exp.period}  {exp.title}, {exp.organization}\n"
            + "\n".join(f"  - {bullet}" for bullet in exp.bullets)
            for exp in profile.experience
        ),
        "/etc/motd": lore.shell_motd,
        "/etc/hostname": lore.hostname,
        "/etc/passwd": "runner:x:1000:1000:just a portfolio, choom:/home/runner:/bin/nsh",
    }
    for project in profile.projects:
        files[f"{HOME}/projects/{project.slug}.md"] = "\n".join(
            [
                f"# {project.title}",
                f"{project.kind} | {project.year}",
                "",
                project.summary,
                "",
                *(f"- {bullet}" for bullet in project.bullets),
                "",
                "tags: " + ", ".join(project.tags),
            ]
        )
    if admin:
        files["/root/blackice.log"] = "\n".join([lore.blackice_title, *lore.blackice_body])
    return VirtualFS(files)
