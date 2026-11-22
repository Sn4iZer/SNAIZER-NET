"""Seal private contact details so they never sit in plain text.

This is obfuscation, not security: anyone with this source can unseal a
value. It keeps numbers out of the repository and away from scrapers that
grep for plain text; the in-app "decrypt" action is the real gate.

Seal a value for ``profile.yaml``::

    python -m snaizer_net.cipher "+212 600 000 000"
"""

import base64
import hashlib
import sys

PREFIX = "snz1:"
KEY = b"SNAIZER//NET::ice-layer-7"


class CipherError(ValueError):
    """Raised when a sealed value is malformed."""


def _keystream(length: int, salt: bytes) -> bytes:
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(KEY + salt + counter.to_bytes(4, "big")).digest()
        counter += 1
    return stream[:length]


def seal(text: str, salt: bytes = b"phone") -> str:
    """Obfuscate ``text`` into a ``snz1:`` token."""
    data = text.encode("utf-8")
    mixed = bytes(a ^ b for a, b in zip(data, _keystream(len(data), salt), strict=True))
    return PREFIX + base64.urlsafe_b64encode(salt + b":" + mixed).decode("ascii")


def unseal(token: str) -> str:
    """Reverse :func:`seal`."""
    if not token.startswith(PREFIX):
        raise CipherError(f"sealed values start with '{PREFIX}'")
    try:
        raw = base64.urlsafe_b64decode(token[len(PREFIX) :].encode("ascii"))
        salt, _, mixed = raw.partition(b":")
        data = bytes(a ^ b for a, b in zip(mixed, _keystream(len(mixed), salt), strict=True))
        return data.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise CipherError(f"cannot unseal value: {error}") from error


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('usage: python -m snaizer_net.cipher "<value to seal>"', file=sys.stderr)
        sys.exit(2)
    print(seal(sys.argv[1]))
