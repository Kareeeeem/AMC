from flask import request, url_for
from marshmallow import ValidationError
from werkzeug.local import LocalProxy

from app import models, db, auth, serializers

from . import v1

GET, PUT, POST, DEL = 'GET', 'PUT', 'POST', 'DELETE'
get_json = LocalProxy(lambda: request.get_json)


@v1.errorhandler(ValidationError)
def validation_error(exception=None):
    return dict(errors=exception.messages), 400


@v1.route('/registration', methods=[POST])
def registration():
    '''Entry point for registration.
    '''
    schema = serializers.UserSchema()
    user_data = schema.load(get_json()).data

    user = models.User(**user_data)
    db.session.add(user)
    db.session.commit()
    rv = schema.dump(user).data
    return rv, 201, {'Location': url_for('.users', id=user.id)}


@v1.route('/users/<hashid:id>')
@auth.token_required
def users(id):
    user = models.User.query.get(id)
    schema = serializers.UserSchema()
    rv = schema.dump(user).data
    return rv


@v1.route('/exercises')
@v1.route('/exercises/<hashid:id>')
def exercises(id=None):
    return {}
