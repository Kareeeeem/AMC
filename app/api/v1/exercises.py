from flask import request
from sqlalchemy.orm import contains_eager

from app import auth, db
from app.models import Exercise, User
from app.serializers import ExerciseSchema, Serializer, ActionSchema
from app.lib import (
    parse_query_params,
    AuthorizationError,
    Pagination,
    get_location_header,
    get_or_404,
)

from . import v1

# EXERCISE ENDPOINTS
# ==================
# /exercises                              GET     retrieve all exercises
# /exercises                              POST    new exercise
# /exercises/<id>                         GET     retrieve a single exercise
# /exercises/<id>                         PUT     edit exercise
# /exercises/<id>                         DELETE  delete exercise
# TODO /exercises/<id>/ratings            GET     all ratings for exercise
# TODO /exercises/<id>/ratings            POST    new rating
# TODO /exercises/<id>/ratings/<user_id>  GET     retrieve rating
# TODO /exercises/<id>/ratings/<user_id>  PUT     edit rating
# TODO /exercises/<id>/ratings/<user_id>  DELETE  delete rating


@v1.route('/exercises', methods=['POST'])
@auth.token_required
def post_exercises():
    '''Post new exercise.'''
    serializer = Serializer(ExerciseSchema, request.args)
    data = dict(author_id=auth.current_user.id,
                **serializer.load(request.get_json()))
    exercise = Exercise.create(db.session, data)
    rv = serializer.dump(exercise)
    return rv, 201, get_location_header('.get_exercise', id=exercise.id)


@v1.route('/exercises', methods=['GET'])
@v1.route('/users/<hashid:favorited_by>/favorites', methods=['GET'])
@v1.route('/users/<hashid:author_id>/exercises', methods=['GET'])
@auth.token_optional
def get_exercises(favorited_by=None, author_id=None):
    '''Get exercise collection, if favorited_by is set then get the
    collection of favorites of the user.'''

    user_id = auth.current_user.id if auth.current_user else None

    # client requests favorites that are not his
    if favorited_by and favorited_by != user_id:
        raise AuthorizationError
    # client request own favorites
    elif favorited_by and favorited_by == user_id:
        ownfavorites = True
    # client requests the general exercise collection
    else:
        ownfavorites = False

    search_params = request.args.get('search')
    order_by = request.args.get('order_by', 'added')

    query = Exercise.query
    query = Exercise.with_avg_rating(query, order_by == 'rating')
    query = Exercise.search(search_params, query, order_by == 'search')
    query = query.order_by(Exercise.created_at.desc())

    if user_id:
        query = Exercise.with_favorited(query, user_id, ownfavorites=ownfavorites)

    if author_id:
        query = query.filter(Exercise.author_id == author_id)

    if 'author' in parse_query_params(request.args, 'extend'):
        query = query.\
            outerjoin(User, Exercise.author).\
            options(contains_eager(Exercise.author))

    page = Pagination(request, query=query)
    return Serializer(ExerciseSchema, request.args).dump_page(page)


@v1.route('/users/<hashid:id>/favorites', methods=['POST'])
@auth.token_required
def add_to_favorites(id):
    '''Add or remove an exercise to favorites.'''
    if auth.current_user.id != id:
        raise AuthorizationError

    data = ActionSchema().load(request.get_json()).data
    exercise = get_or_404(Exercise, data['id'])
    if data['action'] == ActionSchema.APPEND:
        auth.current_user.favorite_exercises.append(exercise)
    else:
        auth.current_user.favorite_exercises = [ex for ex in auth.current_user.favorite_exercises
                                                if ex.id != data['id']]
    db.session.commit()
    return {}, 204


@v1.route('/exercises/<hashid:id>', methods=['GET'])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = get_or_404(Exercise, id)
    return Serializer(ExerciseSchema, request.args).dump(exercise)


@v1.route('/exercises/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_exercise(id):
    '''Update an exercise.'''
    exercise = get_or_404(Exercise, id)
    if auth.current_user.id != exercise.author_id:
        raise AuthorizationError

    serializer = Serializer(ExerciseSchema, request.args)
    exercise.update(db.session, serializer.load(request.get_json()))
    return serializer.dump(exercise)


@v1.route('/exercises/<hashid:id>', methods=['DELETE'])
@auth.token_required
def delete_exercise(id):
    '''Delete an exercise.'''
    exercise = get_or_404(Exercise, id)
    if auth.current_user.id != exercise.author_id:
        raise AuthorizationError

    exercise.delete(db.session)
    return {}, 204
