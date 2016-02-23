'''This module contains plugins and helpers. With an emphasis on those that
need the app's config values.
'''


import fractions
import functools
import random

import bcrypt
import hashids

from flask import (
    abort,
    _app_ctx_stack,
    current_app,
    jsonify,
    request,
    Response,
)
from itsdangerous import (
    BadSignature,
    SignatureExpired,
    TimedJSONWebSignatureSerializer as Serializer,
)
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.types import TypeDecorator
from werkzeug.routing import BaseConverter
from werkzeug.security import safe_str_cmp


class Database(object):
    '''A class that serves as the accesspoint for database operations using
    an SQLAlchemy scoped_session.
    '''
    def __init__(self, app=None):
        self.engine = None
        self.session = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        self.database_uri = app.config['SQLALCHEMY_DATABASE_URI']
        self.echo = app.config.get('SQLALCHEMY_ECHO', False)
        self.create_engine()
        self.create_scoped_session()

        # register teardown function on the application
        app.teardown_appcontext(self.teardown)

    def create_engine(self):
        self.engine = create_engine(self.database_uri,
                                    echo=self.echo,
                                    convert_unicode=True)

    def create_scoped_session(self):
        self.session = scoped_session(sessionmaker(bind=self.engine),
                                      scopefunc=_app_ctx_stack.__ident_func__)

    def teardown(self, exception=None):
        self.session.remove()


class HandleJSONReponse(Response):
    '''Forces the 'application/json' MIME type for dictionary responses.
    '''
    @classmethod
    def force_type(cls, rv, environ=None):
        if isinstance(rv, dict):
            rv = jsonify(rv)
        return super(HandleJSONReponse, cls).force_type(rv, environ)


class IntEncoder(object):
    '''Obfuscates an integer using a modular multiplicative inverse and
    subsequently encodes them using the hashids library. The goal is only to
    thwart the casual onlooker from manually incrementing ids, and also to
    create nicer looking ids, something similar to what you might find on
    youtube and such.

    When used for a web application provide a coprime or else the results will
    be different each time the app is loaded which is obviously not what you
    want.

    It exposes two functions, encode, and decode.
    '''
    def __init__(self, bits=32, coprime=None, salt=''):
        self._bits = bits
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
        rv = self._coprime * integer % self._modulus
        return self.hashid.encode(rv)

    def decode(self, obfuscated_value):
        '''Reverse the proces of encode by decoding with the hashids library
        and then multiplying the result by the modular inverse of coprime
        modulus self._modulus.
        '''
        rv = self.hashid.decode(obfuscated_value)[0]
        return self._inverse * rv % self._modulus

    @property
    def _modulus(self):
        # return the max integer that the specified bits can hold.
        return 2 ** self._bits - 1

    def _find_coprime(self, modulus):
        # every number has a coprime so this loop will always terminate.
        while True:
            other = random.randrange(modulus)
            if fractions.gcd(modulus, other) == 1:
                break
        return other

    def _egcd(self, a, b):
        # wikibooks.org/wiki/Algorithm_Implementation/Mathematics/Extended_Euclidean_algorithm
        if a == 0:
            return (b, 0, 1)
        else:
            gcd, y, x = self._egcd(b % a, a)
            return (gcd, x - (b // a) * y, y)

    def _get_modular_inverse(self, coprime, modulus):
        # wikibooks.org/wiki/Algorithm_Implementation/Mathematics/Extended_Euclidean_algorithm
        gcd, x, y = self._egcd(coprime, modulus)
        if gcd == 1:
            return x % modulus


class FlaskIntEncoder(IntEncoder):
    '''An IntEncoder that gets all it's values from the application config. and
    registers an url converter on the app.
    '''
    def __init__(self, app=None):
        self._bits = None
        self._coprime = None
        self._inverse = None
        self.hashid = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        self._coprime = app.config['INTENCODER_COPRIME']
        self._bits = app.config.get('INTENCODER_BITS', 32)
        self._salt = app.config.get('INTENCODER_SALT', '')
        self._inverse = self._get_modular_inverse(self._coprime, self._modulus)

        if fractions.gcd(self._modulus, self._coprime) != 1:
            message = 'The given coprime is not coprime to {}.'
            raise ValueError(message.format(self._modulus))

        self.hashid = hashids.Hashids(salt=self._salt)
        app.url_map.converters['hashid'] = self.id_converter

    @property
    def id_converter(self):
        class UrlConvertor(BaseConverter):
            '''A converter for use with Flask that encodes and decodes an
            integer value.

            app.url_map.converters['id'] = id_obfuscator.id_converter
            @app.route('<id:user_id>'):
            def user(user_id):
                pass
            '''

            def to_python(self_, value):
                return self.decode(value)

            def to_url(self_, value):
                return self.encode(value)

        return UrlConvertor


class HashIDConverter(BaseConverter):
    '''A converter for use with Flask that encodes and decodes an
    integer value.

    app.url_map.converters['hashid'] = HashIDConverter
    @app.route('<hashid:user_id>'):
    def user(user_id):
        pass
    '''

    SALT = ''

    @property
    def hashid(self):
        return hashids.Hashids(salt=self.SALT)

    def to_python(self, value):
        return self.hashid.decode(value) or abort(404)

    def to_url(self, value):
        return self.hashid.encode(value)

    @classmethod
    def with_salt(cls, salt):
        '''Return a variant with a salt.
        '''
        # implemented like this because it seems like the url converters
        # are invoked outside off the app context so it cannot access the
        # config where the salt is defined.
        class HashIDConverter_(HashIDConverter):
            SALT = salt

        return HashIDConverter_


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


class Auth(object):
    # TODO return proper errors
    # TODO Make it a Flask extension and attach error handlers to the app

    def __init__(self):
        self.verify_token_callback = None

        def error_handler():
            abort(401)

        self.error_handler_callback = error_handler

    def verify_token(self, f):
        '''Registers a callback to be run to validate the token. The callback
        should return True in case of success.
        '''
        self.verify_token_callback = f
        return f

    def error_handler(self, f):
        '''Registers a callback to be run when the token is invalid.
        '''
        self.error_handler_callback = f
        return f

    def login_required(self, f):
        '''Decorate a route with this function to mark it as login required.
        '''
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/master/flask_httpauth.py#L51-L55
            if request.method != 'OPTIONS':
                auth = request.headers.get('Authorization', ' ')
                token_type, token = auth.split(' ')
                if token_type != 'Bearer' or not self.verify_token_callback(token):
                    self.error_handler_callback()
            return f(*args, **kwargs)
        return decorated
