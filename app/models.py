import datetime

from sqlalchemy import (
    Column,
    DateTime,
    DDL,
    event,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Sequence,
    String,
    Text,
    UniqueConstraint
)
from sqlalchemy.sql import expression
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.orm import relationship, backref

from app.lib import SecurityMixin


ID_TYPE = Integer


# TODO extract making and filling in questionnaires with validation into it's own class
# TODO figure out postgresql row_to_json function
# TODO customize id_function


class BaseModel(object):
    @declared_attr
    def __tablename__(cls):
        '''Set the table name to the lowercase version of the class name'''
        return cls.__name__.lower()

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)


Base = declarative_base(cls=BaseModel)
global_id_seq = Sequence('global_id_seq', metadata=Base.metadata)

id_function_signature = 'obscure_id(value bigint)'
create_id_function = '''
CREATE OR REPLACE FUNCTION {name} returns bigint AS $$
DECLARE
l1 int;
l2 int;
r1 int;
r2 int;
i int:=0;
BEGIN
    l1:= (value >> 16) & 65535;
    r1:= value & 65535;
    WHILE i < 3 LOOP
        l2 := r1;
        r2 := l1 # (((({coprime}.0 * r1 + 150889) %% {modulus}) / {modulus}.0) * 32767)::int;
        l1 := l2;
        r1 := r2;
        i := i + 1;
    END LOOP;
    RETURN ((r1 << 16) + l1);
END;
$$ LANGUAGE plpgsql strict immutable;
'''.format(name=id_function_signature, coprime=45896, modulus=1048575)
event.listen(Base.metadata, 'before_create', DDL(create_id_function))

drop_id_function = 'DROP FUNCTION {}'.format(id_function_signature)
event.listen(Base.metadata, 'after_drop', DDL(drop_id_function))


class make_id(expression.FunctionElement):
    type = Integer()


@compiles(make_id, 'postgresql')
def pg_make_id(element, compiler, **kwargs):
    return "obscure_id(nextval('global_id_seq'))"


class ObscureID(object):
    id = Column(ID_TYPE, server_default=make_id(), primary_key=True)


class User(ObscureID, SecurityMixin, Base):
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)

    exercises = relationship(
        'Exercise',
        backref=backref('author', lazy='joined')
    )

    questionnaire_responses = relationship(
        'QuestionnaireResponse',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Questionnaire(ObscureID, Base):
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


class Question(ObscureID, Base):
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


class QuestionnaireResponse(ObscureID, Base):
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


class Exercise(ObscureID, Base):
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'))
