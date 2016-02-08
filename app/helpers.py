import fractions
import random
import hashids

from werkzeug.routing import BaseConverter
from flask import _app_ctx_stack, Response, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


class Database(object):
    '''A class that serves as the accesspoint for database operations using
    an SQLAlchemy scoped_session.
    '''
    def __init__(self, app=None):
        if app:
            self.init_app(app)
        self.engine = None
        self.session = None

    def init_app(self, app):
        self.engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                                    echo=app.config.get('SQLALCHEMY_ECHO', False),
                                    convert_unicode=True)
        self.session = scoped_session(sessionmaker(bind=self.engine),
                                      scopefunc=_app_ctx_stack.__ident_func__)


class HandleJSONReponse(Response):
    @classmethod
    def force_type(cls, rv, environ=None):
        if isinstance(rv, dict):
            rv = jsonify(rv)
        return super(HandleJSONReponse, cls).force_type(rv, environ)


class IntEncoder(object):
    '''Obfuscates an integer using a modular multiplicative inverse. The goal
    is only to thwart the casual onlooker and to provide nicer looking ids,
    something similar to what you might find on youtube and such.

    When used for a web application provide a coprime or else the results will
    be different each time the app is loaded which is obviously not what you
    want.

    It exposes two functions, encode, and decode.
    '''
    def __init__(self, bits=32, coprime=None, salt=''):
        self._modulus = 2 ** bits
        self._coprime = coprime or self._find_coprime(self._modulus)

        if fractions.gcd(self._modulus, self._coprime) != 1:
            message = 'The given coprime is not coprime to {}.'
            raise ValueError(message.format(self._modulus))

        self._inverse = self._get_modular_inverse(self._coprime, self._modulus)
        self.hashid = hashids.Hashids(salt=salt)

    def encode(self, integer):
        '''Encode an integer by first multiplying it by self._coprime molulus
        self._modulus. Then encode it with the hashids library to get nice
        youtube like ids.
        '''
        integer = self._coprime * integer % self._modulus
        return self.hashid.encode(integer)

    def decode(self, obfuscated_value):
        '''Reverse the proces of encode by decoding with the hashids library
        and then multiplying the result by the modular inverse of coprime
        modulus self._modulus.
        '''
        integer = self.hashid.decode(obfuscated_value)[0]
        return self._inverse * integer % self._modulus

    def _find_coprime(self, modulus):
        while True:
            other = random.randrange(modulus)
            if fractions.gcd(modulus, other) == 1:
                break
        return other

    def _get_modular_inverse(self, coprime, modulus):
        gcd, x, y = self._egcd(coprime, modulus)
        if gcd != 1:
            return None
        else:
            return x % modulus

    def _egcd(self, a, b):
        if a == 0:
            return (b, 0, 1)
        else:
            gcd, y, x = self._egcd(b % a, a)
            return (gcd, x - (b // a) * y, y)


class FlaskIntEncoder(IntEncoder):
    '''Gets the modulus bits and coprime from the app config.
    '''
    def __init__(self, app=None):
        self._modulus = None
        self._coprime = None
        self._inverse = None
        self.hashid = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        self._modulus = 2 ** (app.config.get('INTENCODER_BITS', 32))
        self._coprime = app.config['INTENCODER_COPRIME']

        if fractions.gcd(self._modulus, self._coprime) != 1:
            message = 'The given coprime is not coprime to {}.'
            raise ValueError(message.format(self._modulus))

        self._inverse = self._get_modular_inverse(self._coprime, self._modulus)
        self.hashid = hashids.Hashids(salt=app.config.get('INTENCODER_SALT', ''))

    @property
    def id_converter(self):
        '''Returns a converter that uses the encode and decode functions.
        '''
        class UrlConvertor(BaseConverter):
            def to_python(self_, value):
                return self.decode(value)

            def to_url(self_, value):
                return self.encode(value)

        return UrlConvertor
