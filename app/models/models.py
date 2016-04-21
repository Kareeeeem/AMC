from datetime import datetime, timedelta

from psycopg2.extras import NumericRange
from sqlalchemy import (
    Column,
    DateTime,
    DDL,
    event,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    func,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INT4RANGE, JSONB, TSVECTOR
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import nullslast

from meta.orm import db
from meta.mixins import TokenMixin, CreatedUpdatedMixin, CRUDMixin
from meta.columns import IDColumn, PasswordColumn

ID_TYPE = Integer
Base = db.Base


# Relationships do not have any loading stategies configured aside from
# exercise > category. Watch out for N+1 queries.

class User(Base, TokenMixin, CreatedUpdatedMixin, CRUDMixin):
    id = IDColumn()
    password = PasswordColumn()

    username = Column(String(32), unique=True, nullable=False)
    email = Column(String, unique=True)
    last_login = Column(DateTime)

    authored_exercises = relationship(
        'Exercise',
        backref=backref('author'),
    )

    questionnaire_responses = relationship(
        'QuestionnaireResponse',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='QuestionnaireResponse.created_at',
    )

    user_favorite_exercises = relationship(
        'UserFavoriteExercise',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    # a proxy to the exercise values of the above relationship.
    favorite_exercises = association_proxy(
        'user_favorite_exercises',
        'exercise',
        # allows list operations such as appending, popping, extending
        creator=lambda exercise: UserFavoriteExercise(exercise=exercise))

    ratings = relationship(
        'Rating',
        backref='user',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    def login(self, session):
        self.last_login = datetime.utcnow()
        db.session.commit()
        rv = self.generate_auth_token()
        return rv

    def fill_in_questionnaire(self, questionnaire, **kwargs):
        '''Create a questionnaire response.
        '''
        response = QuestionnaireResponse(questionnaire_id=questionnaire.id,
                                         **kwargs)
        self.questionnaire_responses.append(response)
        return response

    def __repr__(self):
        return ('User(id=%r, username=%r, email=%r, created_at=%r, '
                'updated_at=%r, last_login=%r, password=%r)' % (
                    self.id,
                    self.username,
                    self.email,
                    self.created_at,
                    self.updated_at,
                    self.last_login,
                    self.password,
                ))


class UserFavoriteExercise(Base):
    __tablename__ = 'user_favorite_exercise'
    added = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_id = Column(
        ID_TYPE,
        ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True)
    exercise_id = Column(
        ID_TYPE,
        ForeignKey('exercise.id', ondelete='CASCADE'),
        primary_key=True)
    exercise = relationship('Exercise')

    def __repr__(self):
        return ('UserFavoriteExercise(user_id=%r, exercise_id=%r)' % (
            self.user_id,
            self.exercise_id,
        ))


class Rating(Base):
    rating = Column(Float, nullable=False)
    user_id = Column(
        ID_TYPE,
        ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True)
    exercise_id = Column(
        ID_TYPE,
        ForeignKey('exercise.id', ondelete='CASCADE'),
        primary_key=True)
    exercise = relationship('Exercise')

    def __repr__(self):
        return ('UserFavoriteExercise(rating=%r, user_id=%r, exercise_id=%r)' % (
            self.rating,
            self.user_id,
            self.exercise_id,
        ))


class Category(Base):
    id = IDColumn()
    name = Column(String, nullable=False)


class MaxEditTimeExpiredError(Exception):
    pass


class Exercise(Base, CRUDMixin, CreatedUpdatedMixin):
    MAX_EDIT_TIME = timedelta(hours=3)

    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    data = Column(JSONB)
    tsv = Column(TSVECTOR)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))

    category_id = Column(ID_TYPE, ForeignKey('category.id'))
    category = relationship(
        'Category',
        backref='exercises',
        # we always want this but joinedload doesn't play nice with
        # some of the more complicated queries we're doing.
        lazy='subquery',
    )

    @property
    def category_(self):
        return self.category.name

    __table_args__ = Index('ix_exercise_tsv', 'tsv', postgresql_using='gin'),

    @classmethod
    def with_rating(cls, query, user_id):
        '''Returns the query with the average rating as an additional column.
        It's important to not that the SQLAlchemy results will be an iterable
        of tuples, instead of an iterable of Exercises.
        '''

        rating = query.session.\
            query(Rating.exercise_id, Rating.rating).\
            filter(Rating.user_id == user_id).\
            subquery()

        query = query.add_columns(rating.c.rating).\
            outerjoin(rating, rating.c.exercise_id == cls.id).\
            group_by(rating.c.rating)

        return query

    @classmethod
    def with_avg_rating(cls, query, order_by=False):
        '''Returns the query with the average rating as an additional column.
        It's important to not that the SQLAlchemy results will be an iterable
        of tuples, instead of an iterable of Exercises.
        '''

        avg_rating = query.session.\
            query(Rating.exercise_id, func.avg(Rating.rating).label('avg_rating')).\
            group_by(Rating.exercise_id).\
            subquery()

        query = query.add_columns(avg_rating.c.avg_rating).\
            outerjoin(avg_rating, avg_rating.c.exercise_id == cls.id).\
            group_by(cls, avg_rating.c.avg_rating)

        if order_by:
            query = query.order_by(nullslast(avg_rating.c.avg_rating.desc()))

        return query

    @classmethod
    def with_favorited(cls, query, user_id, ownfavorites=False):
        '''Returns the query with the favorited additional column, which will
        be 1 or 0.  It's important to not that the SQLAlchemy results will be
        an iterable of tuples, instead of an iterable of Exercises.
        '''

        isouter = False if ownfavorites else True

        favorited = query.session.\
            query(UserFavoriteExercise.exercise_id).\
            filter_by(user_id=user_id).\
            subquery()

        return query.\
            add_columns(func.count(favorited.c.exercise_id).label('favorited')).\
            join(favorited, favorited.c.exercise_id == cls.id, isouter=isouter)

    @classmethod
    def search(cls, search_terms, query, order_by=False):
        # TODO support more complex queries
        # only support OR queries for now
        # See pg docs http://www.postgresql.org/docs/9.5/static/textsearch.html

        if search_terms:
            search_terms = (' | ').join(search_terms.split())
            query = query.filter(cls.tsv.match(search_terms))

            if order_by:
                query = query.order_by(
                    func.ts_rank(cls.tsv, func.to_tsquery(search_terms)).desc())

        return query

    @property
    def edit_allowed(self):
        '''Only allow edits if exercise is no older than MAX_EDIT_TIME.'''
        return (datetime.utcnow() - self.created_at) < self.MAX_EDIT_TIME

    def update(self, session, data, commit=True):
        if not self.edit_allowed:
            raise MaxEditTimeExpiredError

        return super(Exercise, self).update(session, data, commit=commit)

    def __repr__(self):
        return ('Exercise(id=%r, title=%r, description=%r, data=%r, '
                'author_id=%r, created_at=%r, updated_at=%r)' % (
                    self.id,
                    self.title,
                    self.description,
                    self.data,
                    self.author_id,
                    self.created_at,
                    self.updated_at,
                ))


# This is used for full text search. The application will be in
# dutch, hence the dutch config values for to_tsvector. Also make sure the
# `default_text_search_config` is set to dutch in the application database.
drop_ts_vector_ddl = 'DROP FUNCTION IF EXISTS exercise_trigger()'
ts_vector_ddl = '''
CREATE OR REPLACE FUNCTION exercise_trigger() RETURNS trigger AS $$
begin
  new.tsv :=
    setweight(to_tsvector('pg_catalog.dutch', coalesce(new.title,'')), 'A') ||
    setweight(to_tsvector('pg_catalog.dutch', coalesce(new.description,'')), 'B');
  return new;
end
$$ LANGUAGE plpgsql;
'''

drop_exercise_trigger_ddl = 'DROP TRIGGER IF EXISTS tsvectorupdate ON %(table)s'
exercise_trigger_ddl = '''
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE exercise_trigger()
'''

event.listen(Exercise.__table__, 'after_create', DDL(ts_vector_ddl))
event.listen(Exercise.__table__, 'after_create', DDL(exercise_trigger_ddl))
event.listen(Exercise.__table__, 'before_drop', DDL(drop_exercise_trigger_ddl))
event.listen(Exercise.__table__, 'before_drop', DDL(drop_ts_vector_ddl))


class Questionnaire(Base):
    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(Integer)

    possible_scores = relationship(
        'Score',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    questions = relationship(
        'Question',
        backref='questionnaire',
        collection_class=ordering_list('ordinal'),
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    responses = relationship(
        'QuestionnaireResponse',
        backref=backref('questionnaire'),
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    def __init__(self, **kwargs):
        questions = kwargs.pop('questions')
        self.questions = [Question(**question) for question in questions]

        scores = kwargs.pop('scores')
        for score in scores:
            range = NumericRange(lower=score['min'],
                                 upper=score.get('max', None),
                                 bounds='[]')
            self.possible_scores.append(Score(name=score['name'], range=range))

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    def __repr__(self):
        return ('Questionnaire(id=%r, title=%r, description=%r, version=%r)' % (
            self.id,
            self.title,
            self.description,
            self.version,
        ))


class Score(Base):
    # No standard id. The questionnaire id and name identify the row uniquely.
    range = Column(INT4RANGE, nullable=False)
    name = Column(String(60), nullable=False, primary_key=True)
    questionnaire_id = Column(
        ID_TYPE,
        ForeignKey('questionnaire.id', ondelete='CASCADE'),
        nullable=False,
        primary_key=True,
    )

    def __repr__(self):
        return 'Score(range=%r, name=%r, questionnaire_id=%r)' % (
            self.range,
            self.name,
            self.questionnaire_id,
        )


class Question(Base):
    id = IDColumn()
    text = Column(String, nullable=False)
    ordinal = Column(Integer)

    options = relationship(
        'Option',
        backref='question',
        order_by='Option.value',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    questionnaire_id = Column(
        ID_TYPE,
        ForeignKey('questionnaire.id', ondelete='CASCADE'),
        nullable=False,
    )

    def __init__(self, **kwargs):
        options = kwargs.pop('options')
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.options = [Option(**option) for option in options]

    def __repr__(self):
        return 'Question(id=%r, text=%r, ordinal=%r, questionnaire_id=%r)' % (
            self.id,
            self.text,
            self.ordinal,
            self.questionnaire_id,
        )


class Option(Base):
    __tablename__ = 'option'
    # No standard id. The question id and value identify the row uniquely.
    value = Column(Integer, primary_key=True, autoincrement=False)
    text = Column(String, nullable=False)
    question_id = Column(
        ID_TYPE,
        ForeignKey('question.id', ondelete='CASCADE'),
        primary_key=True
    )

    def __repr__(self):
        return 'Option(value=%r, text=%r, question_id=%r)' % (
            self.value,
            self.text,
            self.question_id,
        )


class Choice(Base):
    value = Column(ID_TYPE, primary_key=True, autoincrement=False)
    question_id = Column(ID_TYPE, primary_key=True, autoincrement=False)
    response_id = Column(
        ID_TYPE,
        ForeignKey('questionnaire_response.id', ondelete='CASCADE'),
        primary_key=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ['value', 'question_id'],
            ['option.value', 'option.question_id'],
            ondelete='CASCADE'
        ),
        UniqueConstraint('question_id', 'response_id')
    )

    def __repr__(self):
        return 'Choice(value=%r, question_id=%r, response_id=%r)' % (
            self.value,
            self.question_id,
            self.response_id,
        )


class QuestionnaireResponse(Base, CreatedUpdatedMixin):
    __tablename__ = 'questionnaire_response'

    id = IDColumn()

    # This relationship joins to Score where the questionnaire ids match
    # and where the sum of the choices values of this response are
    # contained in the score range. Generates the following SQL clause.
    #
    # FROM score
    # WHERE score.questionnaire_id = %(param_1)s AND
    # (score.range @> CAST((SELECT sum(choice.value) AS sum_1
    #  FROM choice
    #  WHERE choice.response_id = %(param_2)s) AS INTEGER))
    score = relationship(
        'Score',
        uselist=False,
        primaryjoin=('''
and_(foreign(Score.questionnaire_id)==QuestionnaireResponse.questionnaire_id,
Score.range.contains(cast(select([func.sum(Choice.value)]).
where(Choice.response_id == QuestionnaireResponse.id).as_scalar(), Integer)))
'''))

    choices = relationship(
        'Choice',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    user_id = Column(
        ID_TYPE,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False
    )

    questionnaire_id = Column(
        ID_TYPE,
        ForeignKey('questionnaire.id', ondelete='CASCADE'),
        nullable=False
    )

    def __init__(self, **kwargs):
        choices = kwargs.pop('choices')
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.choices = [Choice(**choice) for choice in choices]

    def __repr__(self):
        return ('QuestionnaireResponse(user_id=%r, question_id=%r, '
                'created_at=%r, updated_at=%r)' % (
                    self.user_id,
                    self.questionnaire_id,
                    self.created_at,
                    self.updated_at,
                ))


__all__ = [
    'Base',
    'Choice',
    'Category',
    'db',
    'Exercise',
    'MaxEditTimeExpiredError',
    'Option',
    'Question',
    'Questionnaire',
    'QuestionnaireResponse',
    'Rating',
    'User',
    'UserFavoriteExercise',
]
