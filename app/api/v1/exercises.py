from flask import abort, request, g

from app import auth, db
from app.models import Exercise
from app.serializers import ExerciseSchema
from app.exceptions import AuthorizationError
from app.lib import (
    Pagination,
    parse_query_params,
    get_location_header,
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
    schema = ExerciseSchema()
    exercise_data = schema.load(request.get_json()).data
    exercise_data.update(author_id=g.current_user.id)
    exercise = Exercise.create(db.session, exercise_data)
    rv = schema.dump(exercise, many=True).data
    return rv, 201, get_location_header('v1.get_exercise', id=exercise.id)


@v1.route('/exercises', methods=['GET'])
def get_exercises():
    '''Get exercise collection.'''
    query = Exercise.query
    search_terms = request.args.get('search', '')
    if search_terms:
        query = Exercise.search(search_terms, query=query)
    page = Pagination(request, query.count())
    exercises = query.offset(page.offset).limit(page.limit).all()
    schema = ExerciseSchema(page=page, expand=parse_query_params(request.args))
    return schema.dump(exercises, many=True).data


@v1.route('/exercises<hashid:id>', methods=['GET'])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = Exercise.query.get(id)
    if not exercise:
        abort(404)

    schema = ExerciseSchema(expand=parse_query_params(request.args))
    return schema.dump(exercise).data


@v1.route('/exercises<hashid:id>', methods=['PUT'])
@auth.token_required
def put_exercise(id):
    '''Update an exercise.'''
    exercise = Exercise.query.get(id)
    if not exercise:
        abort(404)

    if g.current_user.id != exercise.author_id:
        raise AuthorizationError

    if not exercise.allow_edit():
        # return a better error message
        abort(400)

    schema = ExerciseSchema()
    exercise_data = schema.load(request.get_json()).data
    exercise.update(db.session, exercise_data)
    return schema.dump(exercise).data


@v1.route('/exercises<hashid:id>', methods=['DELETE'])
@auth.token_required
def delete_exercise(id):
    '''Delete an exercise.'''
    exercise = Exercise.query.get(id)
    if not exercise:
        abort(404)

    if g.current_user.id != exercise.author_id:
        raise AuthorizationError

    exercise.delete(db.session)
    return {}, 204
