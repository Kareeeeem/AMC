'''This module contains general utils, some of which require an app context.
'''
import fractions
import functools
import inspect
import random
import math

import hashids
from flask import (
    abort,
    current_app,
    g,
    jsonify,
    request,
    Response,
    url_for,
)
from werkzeug.routing import BaseConverter
from werkzeug.local import LocalProxy

from app.exceptions import AuthorizationError, PaginationError


def parse_query_params(params):
    '''url query params might be given as such: ?expand=param1&expand=param2.
    or as such: ?expand=param1,param2. Or even as a combination of the two.
    Werkzeug saves these params in a multidict. So when ask for
    request.args.getlist('expand'). We might get something like this.

    >>> params = ['one', 'two', 'two', 'tree,four']

    To support this mixed case scenario we first join everything with a comma.
    And then split it.

    >>> parse_query_params(params)
    ['one', 'two', 'tree', 'four']
    '''

    raw_params = params.getlist('expand')
    return ','.join(raw_params).split(',')


class Pagination(object):
    def __init__(self, request, count):
        if count < 1:
            abort(404)

        # the query_params multidict is immutable so make a copy of it.
        self.query_params = request.args.copy()
        self.view_args = request.view_args
        self.endpoint = request.url_rule.endpoint

        # pop the original pagination params and save them.
        self.page = int(self.query_params.pop('page', 1))
        self.per_page = int(self.query_params.pop('per_page', 10))
        self.total_count = count

        if self.page < 1 or self.page > self.pages or self.per_page > 100:
            raise PaginationError(self.page, self.pages, self.per_page)

        self.current_page_url = self.generate_url(page=self.page, per_page=self.per_page)
        self.first_page_url = self.generate_url(page=1, per_page=self.per_page)
        self.last_page_url = self.generate_url(page=self.pages, per_page=self.per_page)

    def generate_url(self, **pagination_params):
        param_dicts = (pagination_params,
                       self.view_args,
                       self.query_params.to_dict(flat=False))
        # combine all these dicts
        params = reduce(lambda a, b: dict(a, **b), param_dicts)
        return url_for(self.endpoint, _external=True, **params)

    @property
    def pages(self):
        return int(math.ceil(self.total_count / float(self.per_page)))

    @property
    def prev_page_url(self):
        if self.page > 1:
            return self.generate_url(page=self.page - 1, per_page=self.per_page)

    @property
    def next_page_url(self):
        if self.page < self.pages:
            return self.generate_url(page=self.page + 1, per_page=self.per_page)

    @property
    def limit(self):
        return self.per_page

    @property
    def offset(self):
        return (self.page - 1) * self.per_page


def parse_rv(rv):
    '''Takes a value and returns a length 3 tuple. The resulting tuple is
    padded with None types if the input variable is other than a tuple or the
    input value is a tuple with a length less than 3.
    '''
    if isinstance(rv, tuple):
        return rv + (None,) * (3 - len(rv))
    else:
        return rv, None, None


def serialize(serializer, many=False, id_param=None, load=True, dump=True):
    '''Decorator that takes care of (de)serializing and validating incoming and
    outgoing data to and from json.
    '''
    def wrapper(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # Sometimes the schema or it's validators want to know about
            # query params for expanding resources, pagination info, etc.
            serializer.context = dict(**request.args)

            if load:
                if id_param:
                    # We let the schema know about the object we are updating
                    # so it will not check for collisions against itself when
                    # validating for uniqueness.
                    update_id = request.view_args[id_param]
                    serializer.context.update(dict(update_id=update_id))

                json_data = request.get_json()
                # Place the parsed json on the g request global.
                g.json = serializer.load(json_data, many=many).data

            rv = f(*args, **kwargs)

            if dump:
                rv, status_or_headers, headers = parse_rv(rv)
                dumped_rv = serializer.dump(rv, many=many).data
                rv = dumped_rv, status_or_headers, headers
            return rv
        return wrapped
    return wrapper


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


class HashID(object):
    '''A converter for use with Flask that encodes and decodes an
    integer value. Registers a url converter for use like so

    >>> app.url_map.converters['hashid'] = HashIDConverter
    >>> @app.route('<hashid:user_id>'):
    >>> def user(user_id):
    >>>     pass
    '''

    def __init__(self, app=None):
        if app:
            self.salt = ''
            self.init_app(app)

    @property
    def hashid(self):
        return hashids.Hashids(salt=self.salt)

    def decode(self, value):
        return self.hashid.decode(value)

    def encode(self, value):
        return self.hashid.encode(value)

    def init_app(self, app):
        self.salt = app.config.get('HASHID_SALT', '')

        class HashIDConverter(BaseConverter):
            def to_python(self_, value):
                try:
                    return self.decode(value)[0]
                except IndexError:
                    abort(404)

            def to_url(self_, value):
                return self.encode(value)

        app.url_map.converters['hashid'] = HashIDConverter


class Auth(object):
    '''AUthorization class that manages an OAuth authorization flow following
    this guide:
    https://stormpath.com/blog/the-ultimate-guide-to-mobile-api-security/
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
        '''Decorate a route with this to require a username/email
        password combination in a form.
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

    def get_user(self, f):
        '''Register a current_user callback as a werkzeug LocalProxy.'''
        self.current_user = LocalProxy(f)

    def authorize_with_token(self, auth_header):
        if request.method != 'OPTIONS':
            token_type, token = auth_header.split(' ')

            if token_type != 'Bearer' or not self.verify_token_callback(token):
                raise AuthorizationError

    def token_optional(self, f):
        '''Decorate a route with this to make token auth optional.
        '''
        # https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/master/flask_httpauth.py#L51-L55
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if 'Authorization' in request.headers:
                self.authorize_with_token(request.headers.get('Authorization'))

            return f(*args, **kwargs)
        return wrapper

    def token_required(self, f):
        '''Decorate a route with this to require a token.
        '''
        # https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/master/flask_httpauth.py#L51-L55
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', None)
            if not auth_header:
                raise AuthorizationError
            self.authorize_with_token(auth_header)
            return f(*args, **kwargs)
        return wrapper


def get_or_404(model, id):
    rv = model.query.get(id)
    if not rv:
        abort(404)
    return rv
