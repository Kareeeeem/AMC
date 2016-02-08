import pytest  # noqa

from app.models import User


def test_user_password(session):
    user = User(username='Kareem',
                password='0000',
                email='kareem@gmail.com',
                bcrypt_rounds=4)
    session.add(user)
    session.commit()
    assert user.id is not None
