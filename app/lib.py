'''This module contains general utils, some of which require an app context.
'''
import fractions
import functools
import inspect
import random

import hashids

from flask import (
    abort,
    current_app,
    jsonify,
    request,
    Response,
    url_for,
)
from werkzeug.routing import BaseConverter
from app.exceptions import AuthorizationError


def get_location_header(route, **kwargs):
    '''Return a location header.
    '''
    return {'Location': url_for(route, **kwargs)}


class ConfigDescriptor(object):
    '''A descriptor that attempts to get a value from the application config.
    '''
    def __init__(self, key, fallback=False, with_fallback=False):
        self.key = key
        self.fallback = fallback
        self.with_fallback = with_fallback

    def __get__(self, obj, type):
        try:
            return current_app.config.get(self.key)
        except RuntimeError as exc:
            if self.with_fallback:
                return self.fallback
            raise exc


class with_app_config(object):
    '''Decorator that accepts any number of keys as arguments and makes those
    application config values available to the decorated class or function. In
    the case of a class the config value is accesible as an attribute (a
    descriptor is placed on the class). In the case of a function it is passed
    as a keyword argument.

    usage:
        >>> app.config['CONFIG_KEY'] = 'hi'

        >>> @with_config('CONFIG_KEY')
        >>> def foo(CONFIG_KEY='bye'):
        >>>    print CONFIG_KEY

        >>> foo()
        >>> 'hi'

        >>> @with_config['CONFIG_KEY']
        >>> class Foo(object):
        >>>     CONFIG_KEY = 'greetings'

        >>> f = Foo()
        >>> f.CONFIG_KEY
        >>> 'hi'

    When the the function or class is used outside of an application context
    it will use the default value if provided.
    '''
    def __init__(self, *keys):
        self.keys = keys

    # If decorated is a class replace the attribute(s) with descriptor(s).  If
    # the class defined it's own value for the config key save the original as
    # a fallback
    def decorate_class(self, cls):
        for key in self.keys:
            with_fallback, fallback = False, None
            try:
                fallback = getattr(cls, key)
                with_fallback = True
            except AttributeError:
                pass
            descriptor = ConfigDescriptor(key, fallback, with_fallback)
            setattr(cls, key, descriptor)
        return cls

    # If decorated is a function inject the config values into kwargs when
    # the function is called.
    def decorate_function(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                kwargs.update({key: current_app.config.get(key)
                               for key in self.keys})
            except RuntimeError:
                pass
            return f(*args, **kwargs)
        return wrapper

    def __call__(self, f):
        if inspect.isclass(f):
            return self.decorate_class(f)
        else:
            return self.decorate_function(f)


class HandleJSONReponse(Response):
    '''Forces the 'application/json' MIME type for dictionary responses.
    '''
    @classmethod
    def force_type(cls, rv, environ=None):
        if isinstance(rv, dict):
            rv = jsonify(rv)
        return super(HandleJSONReponse, cls).force_type(rv, environ)


# This class is no longer used, the implementation of obfuscated ids has been
# moved to the database
class IntEncoder(object):
    '''Obfuscates an integer using a modular multiplicative inverse. The goal
    is only to thwart the casual onlooker from manually incrementing ids, and
    also to create nicer looking ids, something similar to what you might find
    on youtube and such.

    When used for a web application provide a coprime or else the results will
    be different each time the app is loaded which is obviously not what you
    want.

    It exposes two functions, encode, and decode.
    '''
    def __init__(self, bits=32, coprime=None):
        self._bits = bits
        self._coprime = coprime or self._find_coprime(self._modulus)

        if fractions.gcd(self._modulus, self._coprime) != 1:
            message = 'The given coprime is not coprime to {}.'
            raise ValueError(message.format(self._modulus))

        self._inverse = self._get_modular_inverse(self._coprime, self._modulus)

    def encode(self, integer):
        '''Encode an integer by first multiplying it by self._coprime molulus
        self._modulus. Then encode it with the hashids library to get nice
        youtube like ids.
        '''
        return self._coprime * integer % self._modulus

    def decode(self, obfuscated_value):
        '''Reverse the proces of encode by decoding with the hashids library
        and then multiplying the result by the modular inverse of coprime
        modulus self._modulus.
        '''
        return self._inverse * obfuscated_value % self._modulus

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


class Auth(object):
    '''AUthorization class that manages and OAuth authorization flow following
    https://stormpath.com/blog/the-ultimate-guide-to-mobile-api-security/.
    '''
    def __init__(self, app=None):
        self.verify_token_callback = None
        self.verify_login_callback = None

        if app:
            self.init_app(app)

    def init_app(self, app):
        '''Initialize the extension with the app. That means registering a
        default authorization error handlder.
        '''
        @app.errorhandler(AuthorizationError)
        def unauthorized(exception):
            return dict(errors=exception.response), exception.status_code

    def verify_token(self, f):
        '''Registers a callback to be run to validate the token. The callback
        should return True in case of success.
        '''
        self.verify_token_callback = f
        return f

    def verify_login(self, f):
        '''Registers a callback to be run to validate the username or email
        and password. The callback should return True in case of success.
        '''
        self.verify_login_callback = f
        return f

    def login_required(self, f):
        '''Decorate a route with this function to mark it as login required.
        '''
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            form = request.form

            if form.get('grant_type') != 'password':
                raise AuthorizationError

            username = form.get('username')
            password = form.get('password')

            if (not username
                    or not password
                    or not self.verify_login_callback(username, password)):
                raise AuthorizationError

            return f(*args, **kwargs)
        return wrapper

    def token_required(self, f):
        '''Decorate a route with this function to mark it as token required.
        '''
        # https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/master/flask_httpauth.py#L51-L55
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if request.method != 'OPTIONS':
                auth = request.headers.get('Authorization', ' ')
                token_type, token = auth.split(' ')

                if token_type != 'Bearer' or not self.verify_token_callback(token):
                    raise AuthorizationError

            return f(*args, **kwargs)
        return wrapper
