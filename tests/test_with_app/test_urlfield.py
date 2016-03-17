from flask import url_for
from app.serializers import UserSchema  # , ExerciseSchema


def test_url_field(user, session):
    s = UserSchema(only=('href',))
    rv = s.dump(user).data
    assert rv == dict(href=url_for('v1.users', id=user.id))


def test_nested_field_collapsed(user, exercise, session):
    s = UserSchema()
    rv = s.dump(user).data
    assert rv['exercises'][0] == url_for('v1.exercises', id=exercise.id)


def test_nested_field_expanded(user, exercise, session):
    s = UserSchema(context={'expand': 'exercises'})
    rv = s.dump(user).data
    assert isinstance(rv['exercises'][0], dict)
