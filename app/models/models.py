import datetime

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
    )

    def login(self, session):
        self.last_login = datetime.datetime.utcnow()
        db.session.commit()
        rv = self.generate_auth_token()
        return rv


class Questionnaire(Base):
    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(Integer)

    # scores
    # 0-5 subklinisch
    # 5-9 klinisch
    # 10-14 matig
    # > 15 ernstig

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
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.questions = [Question(**question) for question in questions]

    def create_response(self, **kwargs):
        '''Create a questionnaire response and associate it with `self`.
        '''
        response = QuestionnaireResponse(**kwargs)
        self.responses.append(response)
        return response


class Question(Base):
    id = IDColumn()
    text = Column(String, nullable=False)
    ordinal = Column(Integer)

    answers = relationship(
        'Answer',
        backref='question',
        order_by='Answer.value',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
    questionnaire_id = Column(
        ID_TYPE,
        ForeignKey('questionnaire.id', ondelete='CASCADE'),
        nullable=False,
    )

    def __init__(self, **kwargs):
        answers = kwargs.pop('answers')
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        self.answers = [Answer(**answer) for answer in answers]


class Answer(Base):
    # No standard id. The question id and value identifies the row uniquely.
    value = Column(Integer, primary_key=True, autoincrement=False)
    text = Column(String, nullable=False)
    question_id = Column(
        ID_TYPE,
        ForeignKey('question.id', ondelete='CASCADE'),
        primary_key=True
    )


class AnswerResponse(Base):
    __tablename__ = 'answer_response'

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
            ['answer.value', 'answer.question_id'],
            ondelete='CASCADE'
        ),
        UniqueConstraint('question_id', 'response_id')
    )


class QuestionnaireResponse(Base):
    __tablename__ = 'questionnaire_response'

    id = IDColumn()
    choices = relationship(
        'AnswerResponse',
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
        self.choices = [AnswerResponse(**choice) for choice in choices]


class Exercise(Base):
    id = IDColumn()
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))


__all__ = [
    'Answer',
    'AnswerResponse',
    'Base',
    'db',
    'Exercise',
    'Question',
    'Questionnaire',
    'QuestionnaireResponse',
    'User',
]
