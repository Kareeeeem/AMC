import fractions
import functools
import random

import hashids

import bcrypt
from flask import (
    _app_ctx_stack,
    Response,
    jsonify,
    request,
    current_app,
    abort,
)
from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer,
    SignatureExpired,
    BadSignature,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
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
        self.engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'],
                                    echo=app.config.get('SQLALCHEMY_ECHO', False),
                                    convert_unicode=True)
        self.session = scoped_session(sessionmaker(bind=self.engine),
                                      scopefunc=_app_ctx_stack.__ident_func__)


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
        self._bits = app.config.get('INTENCODER_BITS', 32)
        self._coprime = app.config['INTENCODER_COPRIME']

        if fractions.gcd(self._modulus, self._coprime) != 1:
            message = 'The given coprime is not coprime to {}.'
            raise ValueError(message.format(self._modulus))

        self._inverse = self._get_modular_inverse(self._coprime, self._modulus)
        self.hashid = hashids.Hashids(salt=app.config.get('INTENCODER_SALT', ''))
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


class SecurityMixin(object):
    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        if isinstance(password, unicode):
            password = str(password.encode('u8'))

        rounds = current_app.config.get('BCRYPT_ROUNDS', 13)
        self.password_hash = bcrypt.hashpw(password, bcrypt.gensalt(rounds))

    def verify_password(self, password):
        '''Hash the given password and verify it with self.password_hash
        :param str password: the given password.
        '''
        if isinstance(password, unicode):
            password = password.encode('u8')

        if isinstance(self.password_hash, unicode):
            password_hash = self.password_hash.encode('u8')

            return safe_str_cmp(bcrypt.hashpw(password, password_hash),
                                password_hash)

    def generate_auth_token(self, expiration=None, **payload):
        secret_key = current_app.config['SECRET_KEY']
        expiration = expiration or current_app.config.get('TOKEN_EXPIRATION')
        s = Serializer(secret_key, expires_in=expiration)
        return dict(access_token=s.dumps(payload),
                    expires_in=expiration,
                    token_type='bearer')

    @classmethod
    def verify_auth_token(cls, token):
        secret_key = current_app.config['SECRET_KEY']
        s = Serializer(secret_key)
        try:
            return s.loads(token)
        except (SignatureExpired, BadSignature):
            return None


class Auth(object):
    # TODO return proper errors

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
