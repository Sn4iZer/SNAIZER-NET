import pytest

from snaizer_net.cipher import PREFIX, CipherError, seal, unseal


@pytest.mark.parametrize("text", ["+212 627 777 113", "", "émoji ✓", "a" * 200])
def test_round_trip(text):
    token = seal(text)
    assert token.startswith(PREFIX)
    assert text == unseal(token)
    if text:
        assert text not in token


def test_salt_changes_the_token():
    assert seal("+212", salt=b"a") != seal("+212", salt=b"b")
    assert unseal(seal("+212", salt=b"a")) == "+212"


@pytest.mark.parametrize("token", ["+212 627", "snz1:!!!not-base64", "snz1:" + "A" * 3])
def test_malformed_tokens(token):
    with pytest.raises(CipherError):
        unseal(token)
