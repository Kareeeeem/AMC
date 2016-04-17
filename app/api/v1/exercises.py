from flask import request

from app import auth, db
from app.models import Exercise, UserFavoriteExercise, Rating, User
from app.serializers import ExerciseSchema, Serializer
from app.lib import (
    merge_sqla_results,
    AuthorizationError,
    Pagination,
    get_location_header,
    get_or_404,
)

from sqlalchemy import func
from sqlalchemy.orm import aliased, contains_eager

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

    user_id = auth.current_user.id if auth.current_user else None

    # subquery for avarage rating per exercise
    avg_rating = db.session.\
        query(Rating.exercise_id, func.avg(Rating.rating).label('rating')).\
        group_by(Rating.exercise_id).\
        subquery()

    # subquery for favorited exercises
    favorited = db.session.\
        query(UserFavoriteExercise.exercise_id).\
        filter_by(user_id=user_id).\
        subquery()

    # query the exercises and additional info
    query = db.session.\
        query(Exercise, avg_rating.c.rating,
              func.count(favorited.c.exercise_id).label('favorited')).\
        outerjoin(avg_rating, avg_rating.c.exercise_id == Exercise.id).\
        outerjoin(favorited, favorited.c.exercise_id == Exercise.id)

    # apply the search filter
    query = Exercise.search(request.args.get('search'), query=query)

    # join the author
    if True:
        # TODO if expand author
        authoralias = aliased(User)
        query = query.\
            join(authoralias, Exercise.author).\
            options(contains_eager(Exercise.author, alias=authoralias)).\
            group_by(authoralias)

    # or not
    else:
        query = query.group_by(Exercise, avg_rating.c.rating)

    page = Pagination(request, query=query)

    serializer = Serializer(ExerciseSchema, request.args)
    return serializer.dump_page(page, items=merge_sqla_results(page.items))


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
