from flask import request, url_for
from marshmallow import ValidationError

from app import models, db, auth, serializers
from . import v1

GET, PUT, POST, DEL = 'GET', 'PUT', 'POST', 'DELETE'


# USER ENDPOINTS
# ==============
# /users/registration                          POST   register with the app
# /users                                       GET    retrieve all users
# /users/<id>                                  GET    retrieve a single user
# /users/<id>                                  PUT    edit user
# /users/<id>                                  DELETE edit user
# /users/<id>/exercises                        GET    retreive all exercises authored by user
# /users/<id>/ratings                          GET    retreive all ratings authored by user
# /users/<id>/responses                        GET    retreive all responses authored by user

# EXERCISE ENDPOINTS
# ==================
# /exercises                                   GET    retrieve all exercises
# /exercises                                   POST   new exercise
# /exercises/<id>                              GET    retrieve a single exercise
# /exercises/<id>                              PUT    edit exercise
# /exercises/<id>                              DELETE delete exercise
# /exercises/<id>/ratings                      GET    all ratings for exercise
# /exercises/<id>/ratings                      POST   new rating
# /exercises/<id>/ratings/<user_id>            GET    retrieve rating
# /exercises/<id>/ratings/<user_id>            PUT    edit rating
# /exercises/<id>/ratings/<user_id>            DELETE delete rating

# QUESTIONNAIRE ENDPOINTS
# ==================
# /questionnaires                              GET  retrieve all questionnaires
# /questionnaires                              POST new questionnaire
# /questionnaires/<id>                         GET  retrieve a single questionnaire
# /questionnaires/<id>                         PUT  edit questionnaire
# /questionnaires/<id>                         DELETE  delete questionnaire
# /questionnaires/<id>/responses               GET  retrieve all response
# /questionnaires/<id>/responses               POST new response
# /questionnaires/<id>/responses/<response_id> GET  get response
# /questionnaires/<id>/responses/<response_id> PUT  edit response
# /questionnaires/<id>/responses/<response_id> DELETE  delete response

@v1.errorhandler(ValidationError)
def validation_error(exception=None):
    return dict(errors=exception.messages), 400


@v1.route('/registration', methods=[POST])
def registration():
    '''Entry point for registration.
    '''
    schema = serializers.UserSchema()
    user_data = schema.load(request.get_json()).data

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


@v1.route('/users/<hashid:id>/exercises')
def user_exercises(id):
    '''All exercises authored by user.'''
    return {}


@v1.route('/exercises')
@v1.route('/exercises/<hashid:id>')
def exercises(id=None):
    return {}
