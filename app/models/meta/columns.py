import bcrypt
from sqlalchemy import String, Column, Integer, event, Sequence
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from sqlalchemy.types import TypeDecorator
from werkzeug.security import safe_str_cmp

from app.lib import with_app_config
from orm import db

ID_FUNCTION_NAME = 'obscure_id'
ID_FUNCTION_SIGNATURE = '{}(value bigint)'.format(ID_FUNCTION_NAME)
GLOBAL_SEQUENCE_NAME = 'global_id_seq'

# http://blog.joevandyk.com/2013/04/18/generating-random-ids-with-postgresql/
# This is an implemenation of a feistel cipher. It is not secure but provides
# enough obfuscation to accomplish two goals.
# 1. It hides the sequential nature of the rows from the casual onlooker.
# 2. It provides an integer that looks nice when run through base64/62 for
#    good looking urls.
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
drop_id_function_ddl = 'DROP FUNCTION IF EXISTS {id_function_signature}'

# Define global sequence and bind it to the metadata
Sequence(GLOBAL_SEQUENCE_NAME, metadata=db.Base.metadata)


# Register an event on the metadata that executes the create_id_function_dll on
# the database Before anything else is created.
@event.listens_for(db.Base.metadata, 'before_create')
@with_app_config('OBSCURE_ID_KEY', 'OBSCURE_ID_MODULUS')
def create_id(target, conn, **kwargs):
    ddl = create_id_function_ddl.format(
        id_function_signature=ID_FUNCTION_SIGNATURE,
        coprime=kwargs['OBSCURE_ID_KEY'],
        modulus=kwargs['OBSCURE_ID_MODULUS'],
    )
    conn.execute(ddl)


# Register an event on the metadata that executes the drop_id_function_dll on
# the database after everything else is dropped. This way we avoid dependency
# errors as the function will be used as a server default for certain columns.
@event.listens_for(db.Base.metadata, 'after_drop')
def drop_id(target, conn, **kwargs):
    ddl = drop_id_function_ddl.format(id_function_signature=ID_FUNCTION_SIGNATURE)
    conn.execute(ddl)


class make_obscure_id(expression.FunctionElement):
    '''A function expression that that is of type integer.
    '''
    type = Integer()


@compiles(make_obscure_id, 'postgresql')
def pg_make_obscure_id(element, compiler, **kwargs):
    # this compiles a the make_obscure_id functionElement to a statement that
    # inserts the next value of a sequence in our id function.
    return "{id_function_name}(nextval('{sequence_name}'))".format(
        id_function_name=ID_FUNCTION_NAME,
        sequence_name=GLOBAL_SEQUENCE_NAME,
    )


class BcryptStr(str):
    '''Subclass of string that encrypts and compares using Bcrypt.
    '''
    def __new__(cls, value, salt=None, crypt=True, rounds=None):
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if crypt:
            value = bcrypt.hashpw(value, salt or bcrypt.gensalt(rounds))
        return str.__new__(cls, value)

    def __eq__(self, other):
        if not isinstance(other, BcryptStr):
            other = BcryptStr(other, salt=self)
        return safe_str_cmp(self, other)

    def __ne__(self, other):
        return not self.__eq__(other)


@with_app_config('BCRYPT_ROUNDS')
class Password(TypeDecorator):
    '''Persist Bcrypt hashes.'''
    impl = String(128)
    BCRYPT_ROUNDS = 12

    def __init__(self, rounds=None, *args, **kwargs):
        TypeDecorator.__init__(self, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value:
            return BcryptStr(value, rounds=self.BCRYPT_ROUNDS)

    def process_result_value(self, value, dialect):
        return BcryptStr(value, crypt=False)


IDColumn = lambda: Column(Integer, server_default=make_obscure_id(), primary_key=True)
PasswordColumn = lambda: Column(Password, nullable=False)
