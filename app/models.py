import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from app import hashid
from app.lib import SecurityMixin


ID_TYPE = Integer

GlobalId = lambda: Column(ID_TYPE, Sequence('global_id_seq'), primary_key=True)
Created = lambda: Column(DateTime, default=datetime.datetime.utcnow)
Modified = lambda: Column(DateTime, default=datetime.datetime.utcnow,
                          onupdate=datetime.datetime.utcnow)

# TODO extract making and filling in questionnaires with validation into it's own class
# TODO figure out postgresql row_to_json function


class BaseModel(object):
    @declared_attr
    def __tablename__(cls):
        '''Set the table name to the lowercase version of the class name'''
        return cls.__name__.lower()

Base = declarative_base(cls=BaseModel)


class User(Base, SecurityMixin):
    id = GlobalId()
    created = Created()
    modified = Modified()

    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    exercises = relationship(
        'Exercise',
        backref=backref('author', lazy='joined')
    )
    questionnaire_responses = relationship(
        'QuestionnaireResponse',
        cascade='all, delete-orphan',
        passive_deletes=True
    )

    def generate_auth_token(self, expiration=None, **kwargs):
        '''Generate an auth token with the hashed id as the payload.
        '''
        payload = dict(id=hashid.encode(self.id), **kwargs)
        return super(User, self).generate_auth_token(expiration=expiration, **payload)

    @classmethod
    def verify_auth_token(cls, token):
        '''Verify the auth token and return the claims with the decoded id if
        valid and None if invalid.
        '''
        data = super(User, cls).verify_auth_token(token)
        if data:
            data.update(id=hashid.decode(data['id']))
            return data


class Questionnaire(Base):
    id = GlobalId()
    created = Created()
    modified = Modified()

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    version = Column(Integer)

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


class Question(Base):
    id = GlobalId()
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


class QuestionnaireResponse(Base):
    __tablename__ = 'questionnaire_response'

    id = GlobalId()
    created = Created()

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
    id = GlobalId()
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))
