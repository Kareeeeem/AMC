import pytest  # noqa
from sqlalchemy.exc import IntegrityError

from app import models


def test_pw(session):
    u = models.User(
        username='1',
        email='1',
        password='0000',
    )
    session.add(u)
    session.commit()

    u2 = session.query(models.User).first()
    assert u2.password == '0000'


def test_pw_fail(session):
    u = models.User(
        username='1',
        email='1',
        password='000',
    )
    session.add(u)
    session.commit()

    u2 = session.query(models.User).first()
    assert u2.password != '0000'


def test_pw_not_null(session):
    u = models.User(
        username='1',
        email='1',
    )
    session.add(u)

    with pytest.raises(IntegrityError):
        session.commit()
