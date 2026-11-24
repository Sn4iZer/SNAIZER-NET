import random

import pytest
from textual.content import Content

from snaizer_net.shell.commands import FakeShell
from snaizer_net.shell.tokenizer import tokenize
from snaizer_net.shell.vfs import HOME


def plain(result) -> str:
    return "\n".join(Content.from_markup(line).plain for line in result.lines)


@pytest.fixture
def shell(profile, lore) -> FakeShell:
    return FakeShell(profile, lore, user="neo", rng=random.Random(0))


def test_empty_input_does_nothing(shell):
    assert shell.execute("   ").lines == ()


def test_help_lists_every_command(shell):
    text = plain(shell.execute("help"))
    for name in ("help", "whoami", "ls", "cat", "projects", "skills", "contact", "neofetch",
                 "matrix", "theme", "clear", "exit", "grep", "open", "timeline", "fortune",
                 "hack", "history", "decrypt", "classified"):  # fmt: skip
        assert name in text


def test_whoami(shell, profile):
    text = plain(shell.execute("whoami"))
    assert "neo" in text
    assert profile.identity.name in text
    assert "ADMIN" not in text


def test_whoami_admin(profile, lore):
    text = plain(FakeShell(profile, lore, user="snaizer", admin=True).execute("whoami"))
    assert "ADMIN" in text


def test_ls_home_and_projects(shell):
    listing = plain(shell.execute("ls"))
    assert "projects/" in listing
    assert "about.txt" in listing
    assert "pentest-framework.md" in plain(shell.execute("ls projects"))
    assert "no such file" in plain(shell.execute("ls /nope"))


def test_cd_pwd_and_relative_cat(shell):
    shell.execute("cd projects")
    assert plain(shell.execute("pwd")) == f"{HOME}/projects"
    assert "Airbnb NYC" in plain(shell.execute("cat airbnb-nyc.md"))
    shell.execute("cd ..")
    assert plain(shell.execute("pwd")) == HOME
    shell.execute("cd /etc")
    assert "~" not in shell.prompt
    shell.execute("cd")
    assert plain(shell.execute("pwd")) == HOME
    assert "no such directory" in plain(shell.execute("cd /nope"))


def test_cat_variants(shell, profile):
    assert profile.identity.bio[:40] in plain(shell.execute("cat about.txt"))
    assert profile.contact.email in plain(shell.execute("cat ~/contact.txt"))
    assert "usage" in plain(shell.execute("cat"))
    assert "is a directory" in plain(shell.execute("cat projects"))
    assert "no such file" in plain(shell.execute("cat secrets.txt"))
    assert "runner:x:1000" in plain(shell.execute("cat /etc/passwd"))


def test_projects_skills_contact(shell, profile):
    projects = plain(shell.execute("projects"))
    assert all(project.title in projects for project in profile.projects)
    skills = plain(shell.execute("skills"))
    assert "Python (OOP)" in skills
    assert "C1" in skills
    contact = plain(shell.execute("contact"))
    assert profile.contact.email in contact
    assert profile.contact.github_url in contact


def test_neofetch_uses_real_stats(shell, profile):
    text = plain(shell.execute("neofetch"))
    assert profile.identity.name in text
    assert f"Projects: {len(profile.projects)}" in text
    assert f"Awards: {len(profile.awards)}" in text
    assert "Uptime:" in text


def test_ui_actions(shell):
    assert shell.execute("matrix").action == "matrix"
    assert shell.execute("clear").action == "clear"
    assert shell.execute("exit").action == "exit"


def test_theme_command(shell):
    assert "neon-night" in plain(shell.execute("theme"))
    result = shell.execute("theme synthwave")
    assert (result.action, result.argument) == ("theme", "synthwave")
    assert shell.current_theme == "synthwave"
    bad = shell.execute("theme vaporware")
    assert bad.action is None
    assert "unknown theme" in plain(bad)


def test_unknown_command_is_witty_and_names_the_command(shell):
    result = shell.execute("hackthegibson --now")
    assert result.action is None
    assert "hackthegibson" in plain(result)


def test_echo_is_literal(shell):
    assert plain(shell.execute("echo $(whoami) `id` $HOME")) == "$(whoami) `id` $HOME"


def test_completion(shell):
    assert shell.complete("neo") == "neofetch "
    assert shell.complete("c") is None  # cat, cd, clear, contact
    assert shell.complete("cat ab") == "cat about.txt"
    assert shell.complete("cat projects/air") == "cat projects/airbnb-nyc.md"
    assert shell.complete("ls /et") == "ls /etc/"
    assert shell.complete("cat nothing-here") is None


def test_admin_only_file(profile, lore, shell):
    admin = FakeShell(profile, lore, admin=True)
    assert "BLACK-ICE" in plain(admin.execute("cat /root/blackice.log"))
    assert "no such file" in plain(shell.execute("cat /root/blackice.log"))


def test_grep_is_literal_and_highlights(shell):
    text = plain(shell.execute("grep decathlon"))
    assert "experience.txt" in text and "Decathlon, Kenitra" in text
    assert "no match" in plain(shell.execute("grep zzzqqq"))
    assert "usage" in plain(shell.execute("grep"))
    # regex metacharacters are plain text, never patterns
    assert "no match" in plain(shell.execute("grep .*(a+)+$"))


def test_open_project(shell, profile):
    result = shell.execute("open 2")
    assert (result.action, result.argument) == ("open_project", profile.projects[1].slug)
    assert shell.execute("open nids").argument == "nids"
    assert shell.execute("open 99").action is None
    assert "usage" in plain(shell.execute("open"))


def test_timeline_command_lists_new_entries(shell):
    text = plain(shell.execute("timeline"))
    assert "Sales Advisor" in text
    assert "Master d'Excellence in Artificial Intelligence & IoT" in text
    assert text.index("Sales Advisor") < text.index("Freelance IT Customer Support")
    assert text.index("Freelance IT Customer Support") < text.index("E-commerce Founder")


def test_contact_shows_phone_sealed_and_decrypt_reveals_it(shell):
    contact = plain(shell.execute("contact"))
    assert "sealed" in contact and "627" not in contact
    assert "627" not in plain(shell.execute("cat contact.txt"))
    assert "no match" in plain(shell.execute("grep 627"))
    result = shell.execute("decrypt phone")
    assert result.pace == 1
    assert "+212 627 777 113" in plain(result)
    assert "usage" in plain(shell.execute("decrypt"))
    assert "usage" in plain(shell.execute("decrypt email"))


def test_fortune_hack_and_sudo(shell, lore):
    assert plain(shell.execute("fortune")).strip("“”") in lore.shell_fortunes
    hack = shell.execute("hack")
    assert hack.pace == 1
    assert "FICTION" in plain(hack)
    sudo = plain(shell.execute("sudo make me a sandwich"))
    assert "sudoers" in sudo and "Nothing was executed" in sudo


def test_history_records_commands(shell):
    shell.execute("whoami")
    shell.execute("   ")
    shell.execute("ls")
    assert shell.history == ["whoami", "ls"]
    text = plain(shell.execute("history"))
    assert "1  whoami" in text and "3  history" in text


def test_classified_asks_the_ui_to_play_the_file(shell):
    result = shell.execute("classified")
    assert result.action == "classified"
    assert "7-ALPHA" in plain(result)


def test_tokenizer_handles_unbalanced_quotes():
    assert tokenize('echo "unterminated') == ["echo", '"unterminated']
    assert tokenize("echo 'a b' c") == ["echo", "a b", "c"]
