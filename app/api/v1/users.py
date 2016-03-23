import functools

from flask import request, abort, g

from app import models, db, auth, serializers
from app.lib import get_location_header
from app.exceptions import AuthorizationError
from . import v1

GET, PUT, POST, DELETE = 'GET', 'PUT', 'POST', 'DELETE'


def parse_rv(rv):
    '''Takes a value and returns a length 3 tuple. The resulting tuple is
    padded with None types if the input variable is other than a tuple or the
    input value is a tuple with a length less than 3.
    '''
    if isinstance(rv, tuple):
        return rv + (None,) * (3 - len(rv))
    else:
        return rv, None, None


def serialize(serializer, many=False, update_id=None, load=True, dump=True):
    '''Decorator that takes care of (de)serializing and validating incoming and
    outgoing data.
    '''
    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # Sometimes the schema or it's validators want to know about
            # query params for expanding resources, pagination info, etc.
            serializer.context = dict(**request.args)

            if load:
                if update_id:
                    # We let the schema know about the object we are updating
                    # so it will not check for collisions against itself when
                    # validating for uniqueness.
                    id = request.view_args[update_id]
                    serializer.context.update(dict(update_id=id))

                json_data = request.get_json()
                # Place the parsed json on the g request global.
                g.json = serializer.load(json_data, many=many).data

            rv = f(*args, **kwargs)

            if dump:
                rv, status_or_headers, headers = parse_rv(rv)
                dumped_rv = serializer.dump(rv, many=many).data
                rv = dumped_rv, status_or_headers, headers
            return rv
        return wrapped
    return wrapper


# USER ENDPOINTS
# ==============
# /users/                                      POST   register with the app
# /users/<id>                                  GET    retrieve a single user
# /users/<id>                                  PUT    edit user
# /users/<id>                                  DELETE edit user
# /users/<id>/exercises                        GET    retreive all exercises authored by user
# /users/<id>/ratings                          GET    retreive all ratings authored by user
# /users/<id>/responses                        GET    retreive all responses authored by user


@v1.route('/users/', methods=[POST])
def registration():
    '''Register a user.'''
    registerschema = serializers.UserSchema()
    userschema = serializers.UserSchema()

    json_data = request.get_json()
    user_data = registerschema.load(json_data).data
    user = models.User.create(db.session, user_data)
    rv = userschema.dump(user).data
    return rv, 201, get_location_header('.get_user', id=user.id)


@v1.route('/users/', methods=[GET])
def get_users():
    '''Register a user.'''
    users = models.User.query.all()
    userschema = serializers.UserSchema()
    userschema.context = dict(expand=request.args.get('expand', ''))
    return dict(data=userschema.dump(users, many=True).data)


@v1.route('/users/<hashid:id>', methods=[GET])
def get_user(id):
    '''Get a single user profile. '''
    user = models.User.query.get(id)
    if not user:
        abort(404)

    userschema = serializers.UserSchema()
    userschema.context = dict(expand=request.args.get('expand', ''))
    return userschema.dump(user).data


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
    userschema = serializers.UserSchema(exclude=('password',))
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
    exerciseschema = serializers.ExerciseSchema()
    return dict(data=exerciseschema.dump(user.exercises, many=True).data)
