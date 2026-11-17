"""Runtime configuration from CLI flags and environment variables."""

import argparse
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Mode = Literal["local", "web", "ssh"]
ColorMode = Literal["auto", "16", "truecolor"]

MODES: tuple[Mode, ...] = ("local", "web", "ssh")
COLOR_MODES: tuple[ColorMode, ...] = ("auto", "16", "truecolor")

ANIM_FPS = 12
"""Frame rate for every animation; kept <= 15 so SSH and web stay smooth."""

MIN_WIDTH, MIN_HEIGHT = 80, 24
"""Smallest supported terminal; below this a friendly overlay is shown."""

NARROW_WIDTH = 100
"""Below this width the sidebar collapses into a top tab bar."""

TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RunConfig:
    """How the app should behave for this process."""

    mode: Mode = "local"
    animations: bool = True
    skip_intro: bool = False
    colors: ColorMode = "auto"
    content_dir: Path | None = None

    @property
    def is_web(self) -> bool:
        """True when served through textual-serve (enables clickable links)."""
        return self.mode == "web"


def parse_args(
    argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None
) -> RunConfig:
    """Build a :class:`RunConfig`; CLI flags win over environment variables."""
    env = os.environ if environ is None else environ
    env_mode = env.get("SNAIZER_MODE", "local").lower()
    env_colors = env.get("SNAIZER_COLORS", "auto").lower()

    parser = argparse.ArgumentParser(
        prog="snaizer_net", description="SNAIZER//NET cyberpunk terminal portfolio"
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default=env_mode if env_mode in MODES else "local",
        help="runtime mode (default: $SNAIZER_MODE or local)",
    )
    parser.add_argument(
        "--no-anim",
        action="store_true",
        default=env.get("SNAIZER_NO_ANIM", "").lower() in TRUTHY,
        help="disable all animations",
    )
    parser.add_argument(
        "--skip-intro",
        action="store_true",
        default=env.get("SNAIZER_SKIP_INTRO", "").lower() in TRUTHY,
        help="skip the boot sequence and fake login",
    )
    parser.add_argument(
        "--colors",
        choices=COLOR_MODES,
        default=env_colors if env_colors in COLOR_MODES else "auto",
        help="color depth: auto-detect, force 16 colors, or force truecolor",
    )
    parser.add_argument(
        "--content-dir",
        type=Path,
        default=Path(env["SNAIZER_CONTENT_DIR"]) if env.get("SNAIZER_CONTENT_DIR") else None,
        help="directory containing profile.yaml and lore.yaml",
    )
    args = parser.parse_args(argv)
    return RunConfig(
        mode=cast(Mode, args.mode),
        animations=not args.no_anim,
        skip_intro=args.skip_intro,
        colors=cast(ColorMode, args.colors),
        content_dir=args.content_dir,
    )
