from sqlalchemy import (
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from app.lib import SecurityMixin, ObscureIDMixin
from app import db

ID_TYPE = Integer
Base = db.Base


class User(ObscureIDMixin, SecurityMixin, Base):
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)

    exercises = relationship(
        'Exercise',
        backref=backref('author', lazy='joined')
    )

    questionnaire_responses = relationship(
        'QuestionnaireResponse',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class Questionnaire(ObscureIDMixin, Base):
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
        resp = QuestionnaireResponse(**kwargs)
        self.responses.append(resp)
        return resp


class Question(ObscureIDMixin, Base):
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
    question_id = Column(
        ID_TYPE,
        ForeignKey('question.id', ondelete='CASCADE'),
        primary_key=True
    )
    text = Column(String, nullable=False)


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


class QuestionnaireResponse(ObscureIDMixin, Base):
    __tablename__ = 'questionnaire_response'

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


class Exercise(ObscureIDMixin, Base):
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))
