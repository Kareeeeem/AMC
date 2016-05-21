from flask import request

from app import auth, db
from app.models import User
from app.serializers import (
    ProfileSchema,
    Serializer,
    UserSchema,
)
from app.lib import (
    Pagination,
    AuthorizationError,
    get_location_header,
    get_or_404,
)

from . import v1

# USER ENDPOINTS
# ==============
# /users                      POST    register with the app
# /users/<id>                 GET     retrieve a single user
# /users/<id>                 PUT     edit user
# /users/<id>                 DELETE  edit user
# TODO /users/<id>/responses  GET     retreive all responses authored by user


@v1.route('/users', methods=['POST'])
def post_users():
    '''Register a user.'''
    serializer = Serializer(ProfileSchema, request.args)
    user = User.create(db.session, serializer.load(request.get_json()))
    rv = serializer.dump(user)
    return rv, 201, get_location_header('.get_user', id=user.id)


@v1.route('/users', methods=['GET'])
def get_users():
    '''Get users.'''
    serializer = Serializer(UserSchema, request.args)
    query = User.query
    page = Pagination(request, query=query)
    return serializer.dump_page(page)


@v1.route('/users/<hashid:id>', methods=['GET'])
@auth.token_optional
def get_user(id):
    '''Get a single user. '''
    if auth.current_user and auth.current_user.id == id:
        user = auth.current_user
        serializer = Serializer(ProfileSchema, request.args)
    else:
        user = get_or_404(User, id)
        serializer = Serializer(UserSchema, request.args)

    return serializer.dump(user)


@v1.route('/users/profile', methods=['GET'])
@auth.token_required
def get_profile():
    '''Get a single user. '''
    return Serializer(ProfileSchema, request.args).dump(auth.current_user)


@v1.route('/users/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_user(id):
    '''Update a user.'''
    user = get_or_404(User, id)

    if user.id != auth.current_user.id:
        raise AuthorizationError

    serializer = Serializer(ProfileSchema, request.args)
    # This lets the schema validator know about the user to be updated for
    # validating unique columns. So it can ignore false positives.
    serializer.context = dict(update_id=user.id)
    data = serializer.load(request.get_json(), exclude=('password',))
    user.update(db.session, data)
    return serializer.dump(user)


@v1.route('/users/<hashid:id>', methods=['DELETE'])
@auth.token_required
def delete_user(id):
    '''Delete a user.'''
    if id != auth.current_user.id:
        raise AuthorizationError

    auth.current_user.delete(db.session)
    return {}, 204
