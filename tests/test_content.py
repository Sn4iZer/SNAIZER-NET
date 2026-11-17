from pathlib import Path

import pytest
import yaml

from snaizer_net.__main__ import main
from snaizer_net.content import ContentError, load_lore, load_profile, parse_period


def edit_profile(content_dir: Path, mutate) -> Path:
    path = content_dir / "profile.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_real_profile_matches_cv(profile):
    assert profile.identity.name == "Mohammed Tchichi"
    assert profile.identity.handle == "Sn4iZer"
    assert profile.contact.email == "mohammedtchichi03@gmail.com"
    assert profile.contact.github_url == "https://github.com/Sn4iZer"
    assert profile.contact.location == "Tiflet, Morocco"
    assert [edu.period for edu in profile.education] == ["2026-2028", "2025-2026", "2023-2025"]
    assert profile.education[0].degree.startswith("Master's in Artificial Intelligence & IoT")
    assert "Master's" in profile.identity.title
    assert len(profile.projects) == 5
    assert len(profile.awards) == 2
    assert {lang.name: lang.level for lang in profile.languages} == {
        "Arabic": "Native",
        "English": "C1",
        "French": "B1",
    }
    assert profile.projects[0].title == "Data-Driven Pentesting Framework"
    assert any("98%" in bullet for bullet in profile.projects[2].bullets)
    assert {award.place for award in profile.awards} == {"1st Place", "3rd Place"}
    decathlon, ecommerce = profile.experience
    assert (decathlon.title, decathlon.organization) == ("Sport Leader", "Decathlon Kenitra")
    assert decathlon.period == "Jun 2026 - Jul 2026"
    assert len(decathlon.bullets) == 2
    assert "MAD 35,000" in ecommerce.bullets[0]


@pytest.mark.parametrize(
    ("text", "start", "end"),
    [
        ("2023", (2023, 0), (2023, 0)),
        ("2023-2025", (2023, 0), (2025, 0)),
        ("2023-present", (2023, 0), None),
        ("Jun 2026 - Jul 2026", (2026, 6), (2026, 7)),
        ("sep 2026 - present", (2026, 9), None),
    ],
)
def test_parse_period_accepts(text, start, end):
    period = parse_period(text)
    assert period is not None
    assert (period.start, period.end) == (start, end)


@pytest.mark.parametrize("text", ["last year", "2025-2023", "Foo 2026", "Jul 2026 - Jun 2026", ""])
def test_parse_period_rejects(text):
    assert parse_period(text) is None


def test_lore_is_loaded_and_has_required_boot_lines(lore):
    texts = [line.text for line in lore.boot_lines]
    assert "Mounting /dev/portfolio" in texts
    assert "Loading SNAIZER//NET kernel v2.6" in texts
    assert lore.login_hint == "hint: any credentials work, runner."
    assert "FICTION" in lore.blackice_body[0]


def test_missing_file(tmp_path):
    with pytest.raises(ContentError, match="file not found"):
        load_profile(tmp_path / "nope.yaml")


def test_corrupt_yaml(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("identity: [unclosed", encoding="utf-8")
    with pytest.raises(ContentError, match="invalid YAML"):
        load_profile(path)


def test_top_level_must_be_mapping(tmp_path):
    path = tmp_path / "profile.yaml"
    path.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ContentError, match="mapping"):
        load_profile(path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d["identity"].pop("name"), r"identity\.name: missing"),
        (lambda d: d["identity"].update(name="   "), r"identity\.name: must not be empty"),
        (lambda d: d["contact"].update(email="not-an-email"), "not an email"),
        (lambda d: d["skills"][0]["items"][0].update(level=150), "between 0 and 100"),
        (lambda d: d["skills"][0]["items"][0].update(level=True), "expected int"),
        (lambda d: d["projects"][0].update(year=19), "not a valid year"),
        (lambda d: d["projects"][1].update(slug=d["projects"][0]["slug"]), "duplicate slug"),
        (lambda d: d["projects"][0].update(slug="Bad Slug"), "kebab-case"),
        (lambda d: d["projects"][0].update(bullets=[]), "must not be empty"),
        (lambda d: d["education"][0].update(period="last year"), "must look like"),
        (lambda d: d.update(awards="nope"), "expected list"),
    ],
)
def test_validation_errors_point_at_the_field(content_copy, mutate, message):
    path = edit_profile(content_copy, mutate)
    with pytest.raises(ContentError, match=message):
        load_profile(path)


def test_highlights_are_optional(content_copy):
    path = edit_profile(content_copy, lambda d: d.pop("highlights"))
    assert load_profile(path).highlights == ()


def test_lore_missing_section(content_copy):
    path = content_copy / "lore.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.pop("shell")
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ContentError, match="shell: missing"):
        load_lore(path)


def test_main_reports_content_errors_cleanly(content_copy, capsys):
    (content_copy / "profile.yaml").write_text(": : :", encoding="utf-8")
    assert main(["--content-dir", str(content_copy)]) == 2
    err = capsys.readouterr().err
    assert "content error" in err
    assert "profile.yaml" in err
