from flask import request

from app import auth, db
from app.models import User, Exercise, UserFavoriteExercise
from app.serializers import (
    ProfileSchema,
    UserSchema,
    ExerciseSchema,
    ActionSchema,
)
from app.lib import (
    AuthorizationError,
    get_location_header,
    get_or_404,
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
# /users/<id>/favorites       GET     retreive all exercises favorited by user
# TODO /users/<id>/ratings    GET     retreive all ratings authored by user
# TODO /users/<id>/responses  GET     retreive all responses authored by user


@v1.route('/users', methods=['POST'])
def post_users():
    '''Register a user.'''
    schema = ProfileSchema()
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
    schema = UserSchema(page=page,
                        expand=parse_query_params(request.args, key='expand'),
                        exclude=('favorite_exercises',))
    return schema.dump(users, many=True).data


@v1.route('/users/<hashid:id>', methods=['GET'])
@auth.token_optional
def get_user(id):
    '''Get a single user. '''
    expand = parse_query_params(request.args, key='expand')

    if auth.current_user and auth.current_user.id == id:
        user = auth.current_user
        schema = ProfileSchema(expand=expand)
    else:
        user = get_or_404(User, id)
        schema = UserSchema(expand=expand)

    return schema.dump(user).data


@v1.route('/users/profile', methods=['GET'])
@auth.token_required
def get_profile():
    '''Get a single user. '''
    schema = ProfileSchema(expand=parse_query_params(request.args, key='expand'))
    return schema.dump(auth.current_user).data


@v1.route('/users/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_user(id):
    '''Update a user.'''
    user = get_or_404(User, id)

    if user.id != auth.current_user.id:
        raise AuthorizationError

    # TODO change password requires
    schema = ProfileSchema(exclude=('password',))
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
    if id != auth.current_user.id:
        raise AuthorizationError

    auth.current_user.delete(db.session)
    return {}, 204


@v1.route('/users/<hashid:id>/exercises', methods=['GET'])
def get_user_exercises(id):
    '''Get collection of exercises authored by user.'''
    query = Exercise.query.filter(Exercise.author_id == id)
    page = Pagination(request, query.count())
    exercises = query.offset(page.offset).limit(page.limit).all()
    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args, key='expand'))
    return schema.dump(exercises, many=True).data


@v1.route('/users/<hashid:id>/favorites', methods=['GET'])
@auth.token_required
def get_user_favorites(id):
    '''Get collection of exercises authored by user.'''
    if auth.current_user.id != id:
        raise AuthorizationError

    query = Exercise.query.\
        join(UserFavoriteExercise).\
        filter(UserFavoriteExercise.user_id == auth.current_user.id).\
        order_by(UserFavoriteExercise.ordinal.desc())

    page = Pagination(request, query.count())
    exercises = query.offset(page.offset).limit(page.limit).all()
    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args, key='expand'))
    return schema.dump(exercises, many=True).data


@v1.route('/users/<hashid:id>/favorites', methods=['POST'])
@auth.token_required
def add_to_favorites(id):
    '''Add or remove an exercise to favorites.'''
    if auth.current_user.id != id:
        raise AuthorizationError

    data = ActionSchema().load(request.get_json()).data
    exercise = get_or_404(Exercise, data['id'])
    if data['action'] == ActionSchema.FAVORITE:
        auth.current_user.favorite_exercises.append(exercise)
    else:
        UserFavoriteExercise.query.\
            filter(UserFavoriteExercise.user_id == auth.current_user.id,
                   UserFavoriteExercise.exercise_id == data['id']).\
            delete(synchronize_session=False)
    db.session.commit()
    return {}, 204
