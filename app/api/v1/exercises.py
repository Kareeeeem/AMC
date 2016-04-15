from flask import request

from app import auth, db
from app.models import Exercise, UserFavoriteExercise
from app.serializers import ExerciseSchema, Serializer
from app.lib import (
    setattr_and_return,
    AuthorizationError,
    Pagination,
    get_location_header,
    get_or_404,
)

from sqlalchemy import and_

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
@auth.token_optional
def get_exercises():
    '''Get exercise collection.'''
    serializer = Serializer(ExerciseSchema, request.args)
    query = Exercise.search(request.args.get('search'))

    if not auth.current_user:
        page = Pagination(request, query=query)
        return serializer.dump_page(page)

    # If a user authenticated himself we want to know which exercises the
    # authenticated user favorited. We do an outer join to UserFavoriteExercise
    # and add the user_id column to our results. This will add the user_id to
    # any row that contains an exercise the user favorited, and None otherwise.
    # The result could look something like this:
    # [(<an exercise>, <a user id>), (<an exercise>, None)]
    query = query.add_columns(UserFavoriteExercise.user_id).\
        outerjoin(UserFavoriteExercise, and_(
            UserFavoriteExercise.exercise_id == Exercise.id,
            UserFavoriteExercise.user_id == auth.current_user.id))
    page = Pagination(request, query=query)
    items = (setattr_and_return(exercise, 'favorited', bool(user_id))
             for exercise, user_id in page.items)
    return serializer.dump_page(page, items=items)


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
