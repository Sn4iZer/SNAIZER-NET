"""ASCII art: a tiny block font plus the static banners used across screens."""

# 5x5 bitmaps. "#" is a filled cell, "." an empty one.
_GLYPHS: dict[str, tuple[str, ...]] = {
    "A": (".###.", "#...#", "#####", "#...#", "#...#"),
    "C": (".####", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "####.", "#....", "#####"),
    "F": ("#####", "#....", "####.", "#....", "#...."),
    "H": ("#...#", "#...#", "#####", "#...#", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#####"),
    "O": (".###.", "#...#", "#...#", "#...#", ".###."),
    "U": ("#...#", "#...#", "#...#", "#...#", ".###."),
    "G": (".####", "#....", "#..##", "#...#", ".###."),
    "I": ("#####", "..#..", "..#..", "..#..", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#"),
    "R": ("####.", "#...#", "####.", "#..#.", "#...#"),
    "S": (".####", "#....", ".###.", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "...#.", "..#..", ".#...", "#####"),
    "4": ("#...#", "#...#", "#####", "....#", "....#"),
    "/": ("....#", "...#.", "..#..", ".#...", "#...."),
    " ": ("...", "...", "...", "...", "..."),
}
GLYPH_HEIGHT = 5
_HALF_BLOCKS = {(False, False): " ", (True, False): "▀", (False, True): "▄", (True, True): "█"}


def _bitmap(text: str) -> list[str]:
    """Join glyph bitmaps side by side with one empty column between them."""
    rows = [""] * GLYPH_HEIGHT
    for index, char in enumerate(text.upper()):
        glyph = _GLYPHS.get(char, _GLYPHS[" "])
        for row in range(GLYPH_HEIGHT):
            rows[row] += ("." if index else "") + glyph[row]
    return rows


def render_banner(text: str, compact: bool = False) -> list[str]:
    """Render ``text`` with the block font.

    The full version is 5 rows tall using ``█``; the compact version folds two
    bitmap rows into one with half blocks, giving a 3-row banner.
    """
    rows = _bitmap(text)
    if not compact:
        return [row.replace("#", "█").replace(".", " ") for row in rows]
    rows.append("." * len(rows[0]))
    folded = []
    for top, bottom in zip(rows[0::2], rows[1::2], strict=True):
        folded.append(
            "".join(_HALF_BLOCKS[(a == "#", b == "#")] for a, b in zip(top, bottom, strict=True))
        )
    return folded


TROPHY = [
    " ▄▄▄▄▄▄▄▄▄▄▄ ",
    "▐█▀▀▀▀▀▀▀▀▀█▌",
    "▐▌▐███████▌▐▌",
    " ▀▄▐█████▌▄▀ ",
    "   ▀█████▀   ",
    "     ███     ",
    "    ▄███▄    ",
    "  ▐███████▌  ",
]

SKULL = [
    "   ▄▄▄▄▄▄▄▄▄   ",
    " ▄█▀▀     ▀▀█▄ ",
    "▐█  ▄▄   ▄▄  █▌",
    "▐█ ▐██▌ ▐██▌ █▌",
    " ▀█▄  ▄█▄  ▄█▀ ",
    "   █▌▀▀▀▀▀▐█   ",
    "   ▀█▄█▄█▄█▀   ",
]

NEOFETCH_LOGO = [
    "  ▄▄▄▄▄▄▄▄▄▄▄  ",
    " ██▀▀▀▀▀▀▀▀▀▀  ",
    " ██▄▄▄▄▄▄▄▄▄   ",
    "  ▀▀▀▀▀▀▀▀▀██  ",
    "  ▄▄▄▄▄▄▄▄▄██  ",
    "  ▀▀▀▀▀▀▀▀▀▀   ",
    "  //  N E T    ",
]
