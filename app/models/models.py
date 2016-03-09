import datetime
from psycopg2.extras import NumericRange

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INT4RANGE
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from meta.orm import db
from meta.mixins import TokenMixin, CreatedUpdatedMixin
from meta.columns import IDColumn, PasswordColumn

ID_TYPE = Integer
Base = db.Base


class User(Base, TokenMixin, CreatedUpdatedMixin):
    id = IDColumn()
    password = PasswordColumn()

    username = Column(String(32), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    last_login = Column(DateTime)

    exercises = relationship(
        'Exercise',
        backref=backref('author', lazy='joined')
    )

    questionnaire_responses = relationship(
        'QuestionnaireResponse',
        cascade='all, delete-orphan',
        passive_deletes=True,
        order_by='QuestionnaireResponse.created_at',
    )

    def login(self, session):
        self.last_login = datetime.datetime.utcnow()
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
        backref=backref('questionnaire', lazy='joined'),
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


class QuestionnaireResponse(Base, CreatedUpdatedMixin):
    __tablename__ = 'questionnaire_response'

    id = IDColumn()

    # This relationship joins to Score where the questionnaire ids match
    # and where the sum of the choices values of this response are
    # contained in the score range. Generates the following SQL.
    #
    # FROM score
    # WHERE score.questionnaire_id = %(param_1)s AND
    # (score.range @> CAST((SELECT sum(choice.value) AS sum_1
    #  FROM choice
    #  WHERE choice.response_id = %(param_2)s) AS INTEGER))
    score = relationship(
        'Score',
        uselist=False,
        lazy='joined',
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


class Exercise(Base):
    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))


__all__ = [
    'Base',
    'Choice',
    'db',
    'Exercise',
    'Option',
    'Question',
    'Questionnaire',
    'QuestionnaireResponse',
    'User',
]
