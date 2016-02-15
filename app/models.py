import datetime

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    Text,
    ForeignKey,
    Sequence,
)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship

from app import hashid
from app.lib import SecurityMixin

ID_TYPE = Integer


class BaseModel(object):
    @declared_attr
    def __tablename__(cls):
        '''Set the table name to the lowercase version of the class name'''
        return cls.__name__.lower()

    # Using a global sequence for primary key generation to get unique
    # public ids for every row, regardless of the strategy for public ids.
    id = Column(ID_TYPE, Sequence('global_id_seq'), primary_key=True)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    modified = Column(DateTime, default=datetime.datetime.utcnow,
                      onupdate=datetime.datetime.utcnow)


Base = declarative_base(cls=BaseModel)


class User(Base, SecurityMixin):
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    exercises = relationship('Exercise', backref='author')

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


class Exercise(Base):
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id',
                                           ondelete="SET NULL",
                                           onupdate="CASCAdE"))


class Token(Base):
    type = Column(String, unique=True, nullable=False)
    tokens = Column(MutableDict.as_mutable(HSTORE))
