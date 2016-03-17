from flask import url_for
from app.serializers import UserSchema


def test_url_field(user, session):
    s = UserSchema(only=('href',))
    rv = s.dump(user).data
    assert rv == dict(href=url_for('api.users', id=user.id))
