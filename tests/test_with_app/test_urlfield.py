from flask import url_for
from app.serializers import UserSchema, ExerciseSchema


def test_url_field(user, session):
    s = UserSchema(only=('href',))
    rv = s.dump(user).data
    assert rv == dict(href=url_for('v1.get_user', id=user.id))


def test_nested_field_collapsed(user, exercise, session):
    s = UserSchema()
    rv = s.dump(user).data
    assert rv['exercises'] == url_for('v1.get_user_exercises', id=user.id)


def test_nested_field_expanded(user, exercise, session):
    s = UserSchema(expand=['exercises'])
    rv = s.dump(user).data
    assert isinstance(rv['exercises'][0], dict)


def test_nested_field_recursive(user, exercise, session):
    s = ExerciseSchema(expand=['author'])
    rv = s.dump(exercise).data
    assert rv['author'].get('exercises', 'not there') == 'not there'
