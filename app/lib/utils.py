'''This module contains general utils, some of which require an app context.
'''
import functools
import fractions
import random

import hashids

from flask import (
    abort,
    jsonify,
    Response,
    request,
)
from werkzeug.routing import BaseConverter


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
