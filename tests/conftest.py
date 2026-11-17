import shutil
from pathlib import Path

import pytest

from snaizer_net.app import SnaizerApp
from snaizer_net.config import RunConfig
from snaizer_net.content import Lore, Profile, default_content_dir, load_lore, load_profile


@pytest.fixture(scope="session")
def profile() -> Profile:
    return load_profile()


@pytest.fixture(scope="session")
def lore() -> Lore:
    return load_lore()


@pytest.fixture
def content_copy(tmp_path: Path) -> Path:
    """A writable copy of the real content directory."""
    target = tmp_path / "content"
    shutil.copytree(default_content_dir(), target)
    return target


@pytest.fixture
def make_app(profile: Profile, lore: Lore):
    def factory(**overrides) -> SnaizerApp:
        options = {"animations": False}
        options.update(overrides)
        return SnaizerApp(RunConfig(**options), profile, lore)

    return factory


def screen_text(app: SnaizerApp) -> str:
    """Plain text currently drawn on the active screen."""
    return "\n".join(strip.text for strip in app.screen._compositor.render_strips())
