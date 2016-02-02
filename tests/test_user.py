import pytest  # noqa

from app.models import User


def test_user_password(config, session):
    user = User(name='Kareem', password='0000', rounds=config.BCRYPT_ROUNDS)
    session.add(user)
    session.commit()
    assert user.id is not None
