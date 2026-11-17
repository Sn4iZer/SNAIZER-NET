"""Split fake-shell input into words.

Only quoting is understood. Operators such as ``;``, ``|``, ``&&``,
``$(...)`` or backticks are kept as literal text: nothing is ever expanded,
substituted or executed.
"""

import shlex

MAX_INPUT = 512


def tokenize(line: str) -> list[str]:
    """Return the words of ``line``, falling back to whitespace splitting."""
    line = line[:MAX_INPUT]
    try:
        return shlex.split(line, comments=False, posix=True)
    except ValueError:
        return line.split()
