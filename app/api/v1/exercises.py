from flask import abort

from app import models, serializers
from . import v1

GET, PUT, POST, DELETE = 'GET', 'PUT', 'POST', 'DELETE'


# EXERCISE ENDPOINTS
# ==================
# /exercises                                   GET    retrieve all exercises
# /exercises                                   POST   new exercise
# /exercises/<id>                              GET    retrieve a single exercise
# /exercises/<id>                              PUT    edit exercise
# /exercises/<id>                              DELETE delete exercise
# /exercises/<id>/ratings                      GET    all ratings for exercise
# /exercises/<id>/ratings                      POST   new rating
# /exercises/<id>/ratings/<user_id>            GET    retrieve rating
# /exercises/<id>/ratings/<user_id>            PUT    edit rating
# /exercises/<id>/ratings/<user_id>            DELETE delete rating

exerciseschema = serializers.ExerciseSchema()


@v1.route('/exercises', methods=[GET])
def get_exercises():
    '''Get exercise collection.'''
    query = models.Exercise.query
    # TODO filter based on query params
    exercises = query.all()
    return dict(data=exerciseschema.dump(exercises, many=True).data)


@v1.route('/exercises<hashid:id>', methods=[GET])
def get_exercise(id):
    '''Get an exercise.'''
    exercise = models.Exercise.query.get(id)
    if not exercise:
        abort(404)
    return exerciseschema.dump(exercise).data


# @v1.route('/exercises<hashid:id>', methods=[PUT, DELETE])
# def get_exercise(id):
#     exercise = models.Exercise.query.get(id)
#     if not exercise:
#         abort(404)
#     return exerciseschema.dump(exercise).data
