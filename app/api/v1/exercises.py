from flask import abort, request

from app import auth, db
from app.models import Exercise, UserFavoriteExercise
from app.serializers import ExerciseSchema
from app.exceptions import AuthorizationError
from app.lib import (
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
    search_terms = request.args.get('search')

    if auth.current_user:
        # We also want to know which exercises the authenticated user
        # favorited. We do an outer join and ask for the exercise and the
        # user_id.
        query = db.session.query(Exercise, UserFavoriteExercise.user_id).\
            outerjoin(UserFavoriteExercise, and_(
                Exercise.id == UserFavoriteExercise.exercise_id,
                UserFavoriteExercise.user_id == auth.current_user.id
            ))

        query = Exercise.search(search_terms, query=query)
        page = Pagination(request, query.count())
        results = query.offset(page.offset).limit(page.limit).all()

        # The result contains rows of tuples (exercise, user_id or None).  We
        # run setattr in our generator expression to set exercise.favorited to
        # bool(user_id). Setattr itself always returns None, so because of the
        # OR statement the exercise will be placed in the retulting iterable.
        exercises = (setattr(exercise, 'favorited', bool(user_id)) or exercise
                     for exercise, user_id in results)

    else:
        query = Exercise.search(search_terms)
        page = Pagination(request, query.count())
        exercises = query.offset(page.offset).limit(page.limit).all()

    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args))
    return schema.dump(exercises, many=True).data


@v1.route('/exercises/<hashid:id>', methods=['GET'])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = get_or_404(Exercise, id)
    schema = ExerciseSchema(expand=parse_query_params(request.args))
    return schema.dump(exercise).data


@v1.route('/exercises/<hashid:id>', methods=['PUT'])
@auth.token_required
def put_exercise(id):
    '''Update an exercise.'''
    exercise = get_or_404(Exercise, id)
    if auth.current_user.id != exercise.author_id:
        raise AuthorizationError

    if not exercise.allow_edit():
        # TODO return a better error message
        abort(400)

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
