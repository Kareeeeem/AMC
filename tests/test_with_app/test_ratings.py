from app.models import Exercise, User, Rating


def test_give_rating(session):
    u0 = User(username='user0', password='00000000')
    u1 = User(username='user1', password='00000000')
    ex = Exercise(title='title1', description='desc0')
    FUNRATING0 = 4
    EFFECTIVERATING0 = 2
    CLEARRATING0 = 1

    session.add_all([u0, u1, ex])
    session.commit()
    rating = Rating(
        fun=FUNRATING0,
        clear=CLEARRATING0,
        effective=EFFECTIVERATING0,
        exercise_id=ex.id,
        user_id=u0.id)
    session.add(rating)
    session.commit()

    ex_id, rating = session.query(Exercise.id, Rating.rating).\
        join(Rating).\
        filter(Rating.exercise_id == ex.id).\
        first()

    r = (FUNRATING0 + EFFECTIVERATING0 + CLEARRATING0) / 3.0

    # ghetto way of ignoring the last bunch of decimal points. SQL
    # rounds differently than python.
    assert ex_id == ex.id and int(rating * 1000) == int(r * 1000)


def test_avarage_rating(session):
    u0 = User(username='user0', password='00000000')
    u1 = User(username='user1', password='00000000')
    ex = Exercise(title='title1', description='desc0')
    FUNRATING0 = 4
    EFFECTIVERATING0 = 2
    CLEARRATING0 = 1
    AV0 = (FUNRATING0 + EFFECTIVERATING0 + CLEARRATING0) / 3.0

    FUNRATING1 = 1
    EFFECTIVERATING1 = 5
    CLEARRATING1 = 3
    AV1 = (FUNRATING1 + EFFECTIVERATING1 + CLEARRATING1) / 3.0
    AV = (AV0 + AV1) / 2.0

    session.add_all([u0, u1, ex])
    session.commit()
    rating0 = Rating(
        fun=FUNRATING0,
        clear=CLEARRATING0,
        effective=EFFECTIVERATING0,
        exercise_id=ex.id,
        user_id=u0.id)
    rating1 = Rating(
        fun=FUNRATING1,
        clear=CLEARRATING1,
        effective=EFFECTIVERATING1,
        exercise_id=ex.id,
        user_id=u1.id)
    session.add_all([rating0, rating1])
    session.commit()

    ex_id, avg_rating = session.query(Exercise.id, Exercise.avg_rating).first()

    # ghetto way of ignoring the last bunch of decimal points. SQL
    # rounds differently than python.
    assert ex_id == ex.id and int(avg_rating * 1000) == int(AV * 1000)
