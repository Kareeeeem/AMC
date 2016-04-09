from flask import request

from app import auth, db
from app.models import Exercise, UserFavoriteExercise
from app.serializers import ExerciseSchema
from app.lib import (
    AuthorizationError,
    Pagination,
    parse_query_params,
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
    schema = ExerciseSchema()
    exercise_data = schema.load(request.get_json()).data
    exercise_data.update(author_id=auth.current_user.id)
    exercise = Exercise.create(db.session, exercise_data)
    rv = schema.dump(exercise).data
    return rv, 201, get_location_header('v1.get_exercise', id=exercise.id)


@v1.route('/exercises', methods=['GET'])
@auth.token_optional
def get_exercises():
    '''Get exercise collection.'''
    query = Exercise.search(request.args.get('search'))
    page = Pagination(request, query.count())
    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args, key='expand'))

    if not auth.current_user:
        exercises = query.offset(page.offset).limit(page.limit).all()
    else:
        # We want to know which exercises the authenticated user favorited. We
        # do an outer join to UserFavoriteExercise and add the user_id column
        # to our results. This will add the user_id to any row that contains an
        # exercise the user favorited, and None otherwise. The result could
        # look something like this:
        # [(<an exercise>, <a user id>), (<an exercise>, None)]
        results = query.add_columns(UserFavoriteExercise.user_id).\
            outerjoin(UserFavoriteExercise, and_(
                UserFavoriteExercise.exercise_id == Exercise.id,
                UserFavoriteExercise.user_id == auth.current_user.id)).\
            offset(page.offset).limit(page.limit).all()

        exercises = (setattr_and_return(exercise, 'favorited', bool(user_id))
                     for exercise, user_id in results)

    return schema.dump(exercises, many=True).data


def setattr_and_return(obj, key, value):
    '''A setattr function that returns the object. Usefull for setting
    attributes in expressions and comprehensions.
    '''
    setattr(obj, key, value)
    return obj


@v1.route('/exercises/<hashid:id>', methods=['GET'])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = get_or_404(Exercise, id)
    schema = ExerciseSchema(expand=parse_query_params(request.args, key='expand'))
    return schema.dump(exercise).data


@v1.route('/exercises/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_exercise(id):
    '''Update an exercise.'''
    exercise = get_or_404(Exercise, id)
    if auth.current_user.id != exercise.author_id:
        raise AuthorizationError

    schema = ExerciseSchema()
    exercise_data = schema.load(request.get_json()).data
    exercise.update(db.session, exercise_data)
    return schema.dump(exercise).data


@v1.route('/exercises/<hashid:id>', methods=['DELETE'])
@auth.token_required
def delete_exercise(id):
    '''Delete an exercise.'''
    exercise = get_or_404(Exercise, id)
    if auth.current_user.id != exercise.author_id:
        raise AuthorizationError

    exercise.delete(db.session)
    return {}, 204
