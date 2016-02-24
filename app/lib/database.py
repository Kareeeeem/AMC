'''This module contains the database utilities. Some  of which require an
app context.
'''

import datetime
import fractions

import bcrypt

from flask import (
    _app_ctx_stack,
    current_app,
)
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    TimedJSONWebSignatureSerializer as Serializer,
)
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    DDL,
    event,
    Integer,
    Sequence
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm import sessionmaker, scoped_session, class_mapper
from sqlalchemy.sql import expression
from sqlalchemy.types import TypeDecorator
from werkzeug.security import safe_str_cmp

ID_TYPE = Integer
ID_FUNCTION_NAME = 'obscure_id'
ID_FUNCTION_SIGNATURE = '{}(value bigint)'.format(ID_FUNCTION_NAME)
GLOBAL_SEQUENCE_NAME = 'global_id_seq'

drop_id_function_ddl = 'DROP FUNCTION IF EXISTS {id_function_signature}'

# http://blog.joevandyk.com/2013/04/18/generating-random-ids-with-postgresql/
# This is an implemenation of a feistel cipher. It is not secure but provides
# enough obfuscation to accomplish two goals.
# 1. It hides the sequential nature of the rows from the normal onlooker.
# 2. It provides an integer that looks nice when run through base64/62 for
#    nice looking urls.
create_id_function_ddl = '''
CREATE OR REPLACE FUNCTION {id_function_signature} returns bigint AS $$
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
'''


class make_obscure_id(expression.FunctionElement):
    type = Integer()


@compiles(make_obscure_id, 'postgresql')
def pg_make_obscure_id(element, compiler, **kwargs):
    # this compiles a statement that runs the next value of a sequence through
    # our id function.
    return "{id_function_name}(nextval('{sequence_name}'))".format(
        id_function_name=ID_FUNCTION_NAME,
        sequence_name=GLOBAL_SEQUENCE_NAME,
    )


class ObscureIDMixin(object):
    '''A mixin that provides a id column that default to an obscure id.
    '''
    id = Column(ID_TYPE, server_default=make_obscure_id(), primary_key=True)


class _QueryProperty(object):
    '''When accessed it returns a query object attached to the model. Enabling
    querying models with: `Model.query.all()`
    it is syntastic sugar for: `db.session.query`.
    '''
    def __init__(self, db):
        self.db = db

    def __get__(self, instance, owner):
        try:
            mapper = class_mapper(owner)
            if mapper:
                return self.db.session.query(mapper)
        except UnmappedClassError:
            return None


class BaseModel(object):
    @declared_attr
    def __tablename__(cls):
        '''Set the table name to the lowercase version of the class name'''
        return cls.__name__.lower()

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    query = None


class Database(object):
    '''A class that serves as the accesspoint for database operations using an
    SQLAlchemy scoped_session. It also sets up an obscure id function in the
    database.
    '''
    def __init__(self, app=None):
        self.engine = None
        self.session = None
        self.Base = self.make_declarative_base()

        if app:
            self.init_app(app)

    def make_declarative_base(self):
        Base = declarative_base(cls=BaseModel)
        Base.query = _QueryProperty(self)
        return Base

    def init_app(self, app):
        self.database_uri = app.config['SQLALCHEMY_DATABASE_URI']
        self.echo = app.config.get('SQLALCHEMY_ECHO', False)
        self.engine = self.create_engine()
        self.session = self.create_scoped_session()

        id_settings = dict(
            id_function_signature=ID_FUNCTION_SIGNATURE,
            coprime=app.config['OBSCURE_ID_KEY'],
            modulus=app.config['OBSCURE_ID_MODULUS']
        )

        self.register_obscure_id_type(**id_settings)

        # register teardown function on the application
        app.teardown_appcontext(lambda exc: self.session.remove())

    def create_engine(self):
        return create_engine(self.database_uri,
                             echo=self.echo,
                             convert_unicode=True)

    def create_scoped_session(self):
        return scoped_session(sessionmaker(bind=self.engine),
                              scopefunc=_app_ctx_stack.__ident_func__)

    def register_obscure_id_type(self, **settings):
        # The obscure id function uses modular arithmetic. The algorithm
        # requires that the modulus and key are coprime, hence the name coprime
        if fractions.gcd(settings['modulus'], settings['coprime']) != 1:
            message = 'OBSCURE_ID_KEY is not coprime to {}'
            raise ValueError(message.format(settings['modulus']))

        # Create the sequence that that will be used as an input to the id
        # function
        Sequence(GLOBAL_SEQUENCE_NAME, metadata=self.Base.metadata)

        event.listen(
            self.Base.metadata,
            'before_create',
            DDL(create_id_function_ddl.format(**settings)))

        event.listen(
            self.Base.metadata,
            'after_drop',
            DDL(drop_id_function_ddl.format(
                id_function_signature=settings['id_function_signature']
            )))


class BcryptStr(str):
    '''Subclass of string that encrypts and implements string comparisons using
    Bcrypt.
    '''
    def __new__(cls, value, salt=None, crypt=True, rounds=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if crypt:
            if not salt:
                salt = bcrypt.gensalt(rounds or cls.get_rounds())
            value = bcrypt.hashpw(value, salt)
        return str.__new__(cls, value)

    @staticmethod
    def get_rounds():
        return current_app.config.get('BCRYPT_ROUNDS', 12)

    def __eq__(self, other):
        if not isinstance(other, BcryptStr):
            other = BcryptStr(other, salt=self)
        return safe_str_cmp(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)


class Password(TypeDecorator):
    '''Persist Bcrypt hashes.'''
    impl = String(128)

    def __init__(self, *args, **kwargs):
        TypeDecorator.__init__(self, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value:
            return BcryptStr(value)

    def process_result_value(self, value, dialect):
        return BcryptStr(value, crypt=False)


class SecurityMixin(object):
    password = Column(Password, nullable=False)

    @staticmethod
    def get_secret_key():
        return current_app.config['SECRET_KEY']

    @staticmethod
    def get_token_expiration():
        return current_app.config['TOKEN_EXPIRATION']

    def generate_auth_token(self, expiration=None, **payload):
        payload.update(dict(id=self.id))
        s = Serializer(self.get_secret_key(),
                       expires_in=self.get_token_expiration())

        return dict(access_token=s.dumps(payload),
                    expires_in=expiration,
                    token_type='bearer')

    @classmethod
    def verify_auth_token(cls, token):
        s = Serializer(cls.get_secret_key())
        try:
            return s.loads(token)
        except (SignatureExpired, BadSignature):
            return None
