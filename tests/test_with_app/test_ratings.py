from sqlalchemy import func

from app.models import Exercise, User, Rating


def test_give_rating(session):
    u0 = User(username='user0', password='00000000')
    u1 = User(username='user1', password='00000000')
    ex = Exercise(title='title1', description='desc0')
    RATING0 = 4

    session.add_all([u0, u1, ex])
    session.commit()
    rating = Rating(rating=RATING0, exercise_id=ex.id, user_id=u0.id)
    session.add(rating)
    session.commit()

    ex_id, rating = session.query(Exercise.id, Rating.rating).\
        join(Rating).\
        filter(Rating.exercise_id == ex.id).\
        first()

    assert ex_id == ex.id and rating == RATING0


def test_avarage_rating(session):
    u0 = User(username='user0', password='00000000')
    u1 = User(username='user1', password='00000000')
    ex = Exercise(title='title1', description='desc0')
    RATING0 = 4
    RATING1 = 3

    session.add_all([u0, u1, ex])
    session.commit()
    rating0 = Rating(rating=RATING0, exercise_id=ex.id, user_id=u0.id)
    rating1 = Rating(rating=RATING1, exercise_id=ex.id, user_id=u1.id)
    session.add_all([rating0, rating1])
    session.commit()

    avg_rating = session.\
        query(Rating.exercise_id, func.avg(Rating.rating).label('avg_rating')).\
        group_by(Rating.exercise_id).\
        subquery()

    ex_id, avg_rating = session.query(Exercise.id, avg_rating.c.avg_rating).\
        join(avg_rating).\
        group_by(Exercise.id, avg_rating.c.avg_rating).first()

    assert ex_id == ex.id and avg_rating == (RATING0 + RATING1) / float(2)
