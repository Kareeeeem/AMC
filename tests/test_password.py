from app.models.meta.columns import BcryptStr


def test_pw_encrypt():
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    # cast to string because the BcryptStr compare functions hash the 'other'
    # before comparing, rendering this a success.
    assert str(pw) != pw_text


def test_pw_fail():
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0001'
    assert pw != other


def test_pw_success():
    pw_text = '0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0000'
    assert pw == other


def test_pw_encrypt_unicode():
    pw_text = u'0000'
    pw = BcryptStr(pw_text, rounds=4)
    # cast to string because the BcryptStr compare functions hash the 'other'
    # before comparing, rendering this a success.
    assert str(pw) != pw_text


def test_pw_fail_unicode():
    pw_text = u'0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0001'
    assert pw != other


def test_pw_success_unicode():
    pw_text = u'0000'
    pw = BcryptStr(pw_text, rounds=4)
    other = '0000'
    assert pw == other
