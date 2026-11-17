import pytest
from textual.content import Content

from snaizer_net.markup import ZERO_WIDTH_SPACE, safe, tint


@pytest.mark.parametrize(
    "text",
    [
        "plain",
        "x \\",
        "a\\[b]",
        "[$neon-danger]x",
        "[b]x[/b]\\",
        "\\\\\\[x]",
        "[/]",
        "[[",
        "\\",
        "",
    ],
)
def test_safe_text_renders_literally_and_does_not_break_following_tags(text):
    markup = tint("cyan", text) + tint("magenta", "Z")
    plain = Content.from_markup(markup).plain.replace(ZERO_WIDTH_SPACE, "")
    assert plain == text + "Z"


def test_safe_neutralizes_variable_tags():
    content = Content.from_markup(safe("[$neon-danger bold]boom"))
    assert content.spans == []
