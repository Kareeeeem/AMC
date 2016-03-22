from flask import request, abort, g
from marshmallow import ValidationError

from app import models, db, auth, serializers
from app.lib import get_location_header
from app.exceptions import AuthorizationError
from . import v1

GET, PUT, POST, DELETE = 'GET', 'PUT', 'POST', 'DELETE'


# USER ENDPOINTS
# ==============
# /users/                                      POST   register with the app
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

userschema = serializers.UserSchema(exclude=('password',))
registerschema = serializers.UserSchema()
exerciseschema = serializers.ExerciseSchema()


@v1.errorhandler(ValidationError)
def validation_error(exception=None):
    if 'collisions' in exception.messages:
        status_code = 409
    else:
        status_code = 400
    return dict(errors=exception.messages), status_code


@v1.route('/users/', methods=[POST])
def registration():
    '''Register a user.'''
    json_data = request.get_json()
    user_data = registerschema.load(json_data).data
    user = models.User.create(db.session, user_data)
    rv = userschema.dump(user).data
    return rv, 201, get_location_header('.get_user', id=user.id)


@v1.route('/users/<hashid:id>', methods=[GET])
def get_user(id):
    '''Get a single user profile. '''
    user = models.User.query.get(id)
    if not user:
        abort(404)

    rv = userschema.dump(user).data
    return rv


@v1.route('/users/<hashid:id>', methods=[PUT])
@auth.token_required
def put_user(id):
    '''Update a user.'''
    user = models.User.query.get(id)
    if not user:
        abort(404)

    elif user.id != g.current_user.id:
        raise AuthorizationError

    # Make the schema validator know about the user to be updated for
    # validating unique columns. A colission with 'self' is of course not a
    # collision.
    userschema.context = dict(id=user.id)
    json_data = request.get_json()
    user_data = userschema.load(json_data).data
    user.update(db.session, user_data)
    return userschema.dump(user).data


@v1.route('/users/<hashid:id>', methods=[DELETE])
@auth.token_required
def delete_user(id):
    '''Delete a user.'''
    user = models.User.query.get(id)
    if not user:
        abort(404)

    elif user.id != g.current_user.id:
        raise AuthorizationError

    user.delete(db.session)
    return {}, 204


@v1.route('/users/<hashid:id>/exercises', methods=[GET])
def get_user_exercises(id):
    '''Get collection of exercises authored by user.'''
    user = models.User.query.get(id)
    if not user:
        abort(404)
    return dict(data=exerciseschema.dump(user.exercises, many=True).data)


@v1.route('/exercises', methods=[GET])
def get_exercises():
    '''Get exercise collection.'''
    query = models.Exercise.query
    # TODO filter based on query params
    exercises = query.all()
    return dict(data=exerciseschema.dump(exercises, many=True).data)


@v1.route('/exercises<hashid:id>', methods=[GET])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = models.Exercise.query.get(id)
    if not exercise:
        abort(404)
    return exerciseschema.dump(exercise).data


# @v1.route('/exercises<hashid:id>', methods=[PUT, DELETE])
# def get_exercise(id):
#     exercise = models.Exercise.query.get(id)
#     if not exercise:
#         abort(404)
#     return exerciseschema.dump(exercise).data
