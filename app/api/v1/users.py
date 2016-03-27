from flask import request, abort, g

from app import auth, db
from app.exceptions import AuthorizationError, PaginationError
from app.models import User, Exercise
from app.serializers import UserSchema, ExerciseSchema
from app.lib import (
    get_location_header,
    Pagination,
    parse_query_params,
)

from . import v1

# USER ENDPOINTS
# ==============
# /users                      POST    register with the app
# /users/<id>                 GET     retrieve a single user
# /users/<id>                 PUT     edit user
# /users/<id>                 DELETE  edit user
# /users/<id>/exercises       GET     retreive all exercises authored by user
# TODO /users/<id>/ratings    GET     retreive all ratings authored by user
# TODO /users/<id>/responses  GET     retreive all responses authored by user


@v1.errorhandler(PaginationError)
def pagination_error(exc=None):
    return dict(errors=exc.errors), 400


@v1.route('/users', methods=['POST'])
def post_users():
    '''Register a user.'''
    schema = UserSchema()
    user_data = schema.load(request.get_json()).data
    user = User.create(db.session, user_data)
    rv = schema.dump(user).data
    return rv, 201, get_location_header('.get_user', id=user.id)


@v1.route('/users', methods=['GET'])
def get_users():
    '''Get users.'''
    query = User.query
    page = Pagination(request, query.count())
    users = query.offset(page.offset).limit(page.limit).all()
    schema = UserSchema(page=page, expand=parse_query_params(request.args))
    return schema.dump(users, many=True).data


@v1.route('/users/<hashid:id>', methods=['GET'])
def get_user(id):
    '''Get a single user. '''
    user = User.query.get(id)
    if not user:
        abort(404)

    userschema = UserSchema(expand=parse_query_params(request.args))
    return userschema.dump(user).data


@v1.route('/users/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_user(id):
    '''Update a user.'''
    user = User.query.get(id)
    if not user:
        abort(404)

    elif user.id != g.current_user.id:
        raise AuthorizationError

    schema = UserSchema(exclude=('password',))
    # Make the schema validator know about the user to be updated for
    # validating unique columns. A colission with 'self' is of course not a
    # collision.
    schema.context.update(update_id=user.id)
    user_data = schema.load(request.get_json()).data
    user.update(db.session, user_data)
    return schema.dump(user).data


@v1.route('/users/<hashid:id>', methods=['DELETE'])
@auth.token_required
def delete_user(id):
    '''Delete a user.'''
    user = User.query.get(id)
    if not user:
        abort(404)

    elif user.id != g.current_user.id:
        raise AuthorizationError

    user.delete(db.session)
    return {}, 204


@v1.route('/users/<hashid:id>/exercises', methods=['GET'])
def get_user_exercises(id):
    '''Get collection of exercises authored by user.'''
    user = User.query.get(id)
    if not user:
        abort(404)

    query = Exercise.query.filter(Exercise.author_id == user.id)
    page = Pagination(request, query.count())
    exercises = query.offset(page.offset).limit(page.limit).all()
    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args))
    return schema.dump(exercises, many=True).data
