import pytest  # noqa

from app.models.meta.columns import BcryptStr


def test_pw_encrypt():
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    assert str(pw) != pw_text


def test_pw_fail():
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0001'
    assert pw != other


def test_pw_success(session):
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0000'
    assert pw == other
