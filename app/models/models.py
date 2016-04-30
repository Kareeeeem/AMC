from datetime import datetime, timedelta

from psycopg2.extras import NumericRange
from sqlalchemy import (
    Float,
    CheckConstraint,
    Boolean,
    Column,
    DateTime,
    DDL,
    event,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INT4RANGE, JSONB, TSVECTOR
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref
# from sqlalchemy.sql.expression import nullslast

from meta.columns import IDColumn, PasswordColumn
from meta.mixins import TokenMixin, CreatedUpdatedMixin, CRUDMixin
from meta.orm import db

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
    rating = Column(Integer,
                    CheckConstraint('rating>0'),
                    CheckConstraint('rating<6'),
                    nullable=False,
                    )

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
    name = Column(String, unique=True, nullable=False)


class MaxEditTimeExpiredError(Exception):
    pass


class Exercise(Base, CRUDMixin, CreatedUpdatedMixin):
    MAX_EDIT_TIME = timedelta(hours=3)

    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    data = Column(JSONB)
    difficulty = Column(Integer, default=0)
    group_exercise = Column(Boolean, default=False)
    private_exercise = Column(Boolean, default=False)
    duration = Column(INT4RANGE)
    tsv = Column(TSVECTOR)
    avg_rating = Column(Float)
    popularity = Column(Float)

    author_id = Column(ID_TYPE, ForeignKey('user.id'))
    category_id = Column(ID_TYPE, ForeignKey('category.id'))
    category = relationship(
        'Category',
        backref='exercises',
        # we always want this but joinedload doesn't play nice with
        # some of the more complicated queries we're doing.
        lazy='joined',
    )

    @property
    def category_name(self):
        return self.category.name

    __table_args__ = Index('ix_exercise_tsv', 'tsv', postgresql_using='gin'),

    @property
    def edit_allowed(self):
        '''Only allow edits if exercise is no older than MAX_EDIT_TIME.'''
        return (datetime.utcnow() - self.created_at) < self.MAX_EDIT_TIME

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


# create a function to calculate the bayesian score based on a 5 star rating
# system.
# http://julesjacobs.github.io/2015/08/17/bayesian-scoring-of-ratings.html
# Will return the default popularity if id is NULL. Which is usefull for
# setting it in a trigger.
bayesian_ddl = '''
CREATE OR REPLACE FUNCTION bayesian(id bigint) returns FLOAT AS $$
DECLARE
utilities INT[];
pretend_votes INT[];
votes_count INT[];
votes INT[];
sum_vu INT;
ex_id BIGINT;
does_exist BOOLEAN;
BEGIN
    ex_id := id;
    utilities := '{-30, 2, 3, 4, 70}'::INT[];
    pretend_votes := '{2, 2, 2, 2, 2}'::INT[];
    SELECT INTO votes_count ARRAY[
        coalesce(count(rating) filter (where rating = 1), 0),
        coalesce(count(rating) filter (where rating = 2), 0),
        coalesce(count(rating) filter (where rating = 3), 0),
        coalesce(count(rating) filter (where rating = 4), 0),
        coalesce(count(rating) filter (where rating = 5), 0)
    ] FROM rating where exercise_id = ex_id;

    SELECT INTO votes array(SELECT a+b FROM unnest(pretend_votes, votes_count) x(a,b));
    SELECT INTO sum_vu SUM(v) FROM UNNEST(array(SELECT a*b FROM unnest(votes, utilities) x(a,b))) v;
    RETURN sum_vu / (SELECT SUM(v)::FLOAT FROM UNNEST(votes) v);
END;
$$ LANGUAGE plpgsql strict;
'''

event.listen(Base.metadata, 'after_create', DDL(bayesian_ddl))
event.listen(Base.metadata, 'after_drop', DDL('DROP FUNCTION IF EXISTS bayesian(bigint)'))

drop_rating_trigger_ddl = 'DROP FUNCTION IF EXISTS rating_trigger()'
create_rating_trigger_ddl = '''
CREATE OR REPLACE FUNCTION rating_trigger() RETURNS trigger as $$
BEGIN
    IF (TG_OP = 'DELETE') THEN
        UPDATE exercise
        SET popularity=bayesian(old.exercise_id),avg_rating=(SELECT avg(rating) FROM rating WHERE exercise_id=old.exercise_id)
        WHERE id=old.exercise_id;
        RETURN OLD;
    ELSE
        UPDATE exercise
        SET popularity=bayesian(new.exercise_id),avg_rating=(SELECT avg(rating) FROM rating WHERE exercise_id=new.exercise_id)
        WHERE id=new.exercise_id;
        RETURN new;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
'''

drop_default_popularity_ddl = 'DROP FUNCTION IF EXISTS default_popularity()'
create_default_popularity_ddl = '''
CREATE OR REPLACE FUNCTION default_popularity() RETURNS trigger as $$
BEGIN
new.popularity := bayesian(new.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
'''

drop_default_popularity_trigger_ddl = 'DROP TRIGGER IF EXISTS set_default_popularity ON %(table)s'
create_default_popularity_trigger_ddl = '''
CREATE TRIGGER set_default_popularity BEFORE INSERT
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE default_popularity();
'''

drop_set_ratings_ddl = 'DROP TRIGGER IF EXISTS set_ratings ON %(table)s'
create_set_ratings_ddl = '''
CREATE TRIGGER set_ratings AFTER INSERT OR UPDATE OR DELETE
ON %(table)s FOR EACH ROW EXECUTE PROCEDURE rating_trigger();
'''

event.listen(Rating.__table__, 'after_create', DDL(create_rating_trigger_ddl))
event.listen(Rating.__table__, 'after_create', DDL(create_set_ratings_ddl))
event.listen(Rating.__table__, 'before_drop', DDL(drop_set_ratings_ddl))
event.listen(Rating.__table__, 'before_drop', DDL(drop_rating_trigger_ddl))

event.listen(Exercise.__table__, 'after_create', DDL(create_default_popularity_ddl))
event.listen(Exercise.__table__, 'after_create', DDL(create_default_popularity_trigger_ddl))

event.listen(Exercise.__table__, 'before_drop', DDL(drop_default_popularity_trigger_ddl))
event.listen(Exercise.__table__, 'before_drop', DDL(drop_default_popularity_ddl))

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
