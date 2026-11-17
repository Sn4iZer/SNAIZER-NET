"""Entry point: ``python -m snaizer_net``."""

import os
import sys
from collections.abc import Sequence

from rich.console import Console

from snaizer_net.config import parse_args
from snaizer_net.content import ContentError, default_content_dir, load_lore, load_profile


def main(argv: Sequence[str] | None = None) -> int:
    """Load content, run the TUI and return a process exit code."""
    config = parse_args(argv)
    if config.mode == "ssh":
        # shutil.get_terminal_size() prefers these over the PTY size, which
        # would freeze the layout after the first window resize.
        os.environ.pop("COLUMNS", None)
        os.environ.pop("LINES", None)

    content_dir = config.content_dir or default_content_dir()
    try:
        profile = load_profile(content_dir / "profile.yaml")
        lore = load_lore(content_dir / "lore.yaml")
    except ContentError as error:
        console = Console(stderr=True)
        console.print("[bold #ff3355]SNAIZER//NET: content error[/]")
        console.print(str(error), markup=False, highlight=False)
        console.print("[#6b7a99]Fix the file (see README, 'Editing your content') and retry.[/]")
        return 2

    from snaizer_net.app import SnaizerApp  # deferred: keeps content errors fast

    SnaizerApp(config, profile, lore).run()
    if config.mode != "web":
        print("\nlink closed. stay frosty, runner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
