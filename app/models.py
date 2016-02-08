import datetime

import bcrypt
from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    SignatureExpired,
    BadSignature,
)
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    Text,
    ForeignKey,
    Sequence,
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship
from werkzeug.security import safe_str_cmp

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


class User(Base):
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    exercises = relationship('Exercise', backref='author')

    def __init__(self, *args, **kwargs):
        self.rounds = kwargs.pop('bcrypt_rounds', 12)
        return super(User, self).__init__(*args, **kwargs)

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    @password.setter
    def password(self, password):
        if isinstance(password, unicode):
            password = str(password.encode('u8'))

        self.password_hash = bcrypt.hashpw(password, bcrypt.gensalt(self.rounds))

    def verify_password(self, password):
        '''Hash the given password and verify it with self.password_hash
        :param str password: the given password.
        '''
        password_hash = self.password_hash

        if isinstance(password, unicode):
            password = password.encode('u8')
        if isinstance(self.password_hash, unicode):
            password_hash = self.password_hash.encode('u8')

        return safe_str_cmp(bcrypt.hashpw(password, password_hash),
                            password_hash)

    def generate_auth_token(self, secret_key, expiration=3600):
        s = Serializer(secret_key, expires_in=expiration)
        return s.dumps({'id': self.id})

    @classmethod
    def verify_auth_token(cls, session, secret_key, token):
        s = Serializer(secret_key)
        try:
            data = s.loads(token)
        except (SignatureExpired, BadSignature):
            return None
        user = session.query(cls).get(data['id'])
        return user


class Exercise(Base):
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    author_id = Column(ID_TYPE, ForeignKey('user.id'), nullable=False)
