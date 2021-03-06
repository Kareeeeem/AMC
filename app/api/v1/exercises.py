from flask import request, abort
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import and_, func, desc, asc
from sqlalchemy.sql.expression import nullslast

from app import auth, db
from app.models import Exercise, Category, Rating, UserFavoriteExercise, User
from app.serializers import (
    ExerciseSchema,
    Serializer,
    ActionSchema,
    RatingSchema,
)
from app.lib import (
    setattr_and_return,
    parse_query_params,
    AuthorizationError,
    Pagination,
    get_location_header,
    get_or_404,
)

from . import v1


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
@auth.token_optional
def get_exercises(favorited_by=None):
    '''Get exercise collection, if favorited_by is set then get the
    collection of favorites of the user.'''

    user_id = auth.current_user.id if auth.current_user else None

    # client requests favorites that are not his.
    if favorited_by and favorited_by != user_id:
        raise AuthorizationError

    search = request.args.get('search')
    category = request.args.get('category')
    order_by = request.args.get('order_by')
    author = request.args.get('author')

    orderfunc = desc
    if order_by and len(order_by) > 0 and order_by[-1] in '+ -'.split():
        if order_by[-1] == '+':
            orderfunc = asc
        order_by = order_by[:-1]

    query = Exercise.query

    if search:
        search_terms = (' | ').join(search.split())
        query = query.add_columns(func.ts_rank(
            Exercise.tsv, func.to_tsquery(search_terms)).label('search_rank')).\
            filter(Exercise.tsv.match(search_terms))

        if order_by == 'relevance':
            query = query.order_by(nullslast(orderfunc('search_rank')))

    if user_id:
        user_rating = aliased(Rating, name='user_rating')

        query = query.add_entity(user_rating).\
            outerjoin(user_rating, and_(user_rating.exercise_id == Exercise.id,
                                        user_rating.user_id == user_id))

        if order_by == 'user_rating':
            query = query.order_by(nullslast(orderfunc(user_rating.rating)))
        elif order_by == 'user_fun_rating':
            query = query.order_by(nullslast(orderfunc(user_rating.fun)))
        elif order_by == 'user_effective_rating':
            query = query.order_by(nullslast(orderfunc(user_rating.effective)))
        elif order_by == 'user_clear_rating':
            query = query.order_by(nullslast(orderfunc(user_rating.clear)))

        # when if favorited_by is not None then we only want the user favorites
        # and isouter will be set to False. Meaning we will do an inner join If
        # favorited_by is None then isouter will be True and we will do an
        # outer join meaning we want to know which exercises the user favorited
        # but we want all of them.
        isouter = not bool(favorited_by)

        # include a column from the UserFavoriteExercise table or `0`.
        # this will get serialized as a Boolean to signify favorited or not.
        query = query.\
            add_columns(func.coalesce(UserFavoriteExercise.exercise_id, 0).label('favorited')).\
            join(UserFavoriteExercise,
                 and_(UserFavoriteExercise.exercise_id == Exercise.id,
                      UserFavoriteExercise.user_id == user_id),
                 isouter=isouter)

    if author:
        query = query.join(User, and_(User.id == Exercise.author_id, User.username == author))

    if category:
        category = parse_query_params(request.args, key='category')
        query = query.join(Category).filter(Category.name.in_(category))

    if 'author' in parse_query_params(request.args, key='expand'):
        query = query.options(joinedload(Exercise.author))

    if order_by in ['average_rating', 'rating']:
        query = query.order_by(nullslast(orderfunc(Exercise.avg_rating)))
    elif order_by == 'average_fun_rating':
        query = query.order_by(nullslast(orderfunc(Exercise.avg_fun_rating)))
    elif order_by == 'average_clear_rating':
        query = query.order_by(nullslast(orderfunc(Exercise.avg_clear_rating)))
    elif order_by == 'average_effective_rating':
        query = query.order_by(nullslast(orderfunc(Exercise.avg_effective_rating)))
    elif order_by == 'popularity':
        query = query.order_by(nullslast(orderfunc(Exercise.popularity)))
    elif order_by == 'updated_at':
        query = query.order_by(orderfunc(Exercise.updated_at))
    else:
        query = query.order_by(orderfunc(Exercise.created_at))

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
    if data['action'] == ActionSchema.FAVORITE:
        auth.current_user.favorite_exercises.append(exercise)
    else:
        auth.current_user.favorite_exercises = [
            ex for ex in auth.current_user.favorite_exercises if ex.id != data['id']]

    db.session.commit()
    return {}, 204


@v1.route('/exercises/<hashid:id>', methods=['GET'])
@auth.token_optional
def get_exercise(id):
    '''Get an exercise.'''
    query = Exercise.query.filter(Exercise.id == id)

    if auth.current_user:
        result = query.add_entity(Rating).\
            join(Rating).\
            filter(Rating.user_id == auth.current_user.id).\
            first()

        try:
            exercise = setattr_and_return(result[0], 'user_rating', result[1])
        except TypeError:
            exercise = None
    else:
        exercise = query.first()

    if not exercise:
        abort(404)

    serializer = Serializer(ExerciseSchema, request.args)
    return serializer.dump(exercise)


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


@v1.route('/exercises/<hashid:id>/ratings', methods=['POST'])
@auth.token_required
def rate_exercise(id):
    '''Rate an exercise, or update previous rating.'''
    exercise = get_or_404(Exercise, id)
    data = Serializer(RatingSchema).load(request.get_json())

    rating = Rating.query.filter(
        Rating.exercise_id == exercise.id,
        Rating.user_id == auth.current_user.id).\
        first()

    if not rating:
        # POST is basically a "do what you want" method. So strictly speaking
        # updating a previous score doesn't violate any rules.
        rating = Rating(exercise_id=exercise.id, user_id=auth.current_user.id)
        db.session.add(rating)

    for key, value in data.iteritems():
        setattr(rating, key, value)

    db.session.commit()
    return {}, 204


@v1.route('/exercises/categories', methods=['GET'])
def get_categories():
    '''Get a list of available categories.'''
    categories = Category.query.all()
    return dict(categories=[c.name for c in categories])
