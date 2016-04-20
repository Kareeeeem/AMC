import fractions
import random
import functools
import inspect

from flask import url_for, current_app, Response, jsonify, abort


class Enum(frozenset):
    '''A ghetto Enum implementation. A set that allows attribute access.
    '''
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


def setattr_and_return(obj, key, value):
    '''A setattr function that returns the object. Usefull for setting
    attributes in expressions and comprehensions.
    '''
    setattr(obj, key, value)
    return obj


def merge_sqla_results(rows):
    '''Merges an SQLAlchemy result. SQLAlchemy returns lists of namedtuples.
    For example a tuple with the items UserObject, attr1, attr2. This function
    is usefull for setting attr1 and attr2 on the UserObject and then returning
    an iterable of UserObjects.
    '''
    for row in rows:
        for field in row._fields[1:]:
            setattr(row[0], field, getattr(row, field))
        yield row[0]


def parse_query_params(params, key):
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

    raw_params = params.getlist(key)
    return ','.join(raw_params).split(',')


def parse_rv(rv):
    '''Takes a value and returns a length 3 tuple. The resulting tuple is
    padded with None types if the input variable is other than a tuple or the
    input value is a tuple with a length less than 3.
    '''
    if isinstance(rv, tuple):
        return rv + (None,) * (3 - len(rv))
    else:
        return rv, None, None


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


def get_or_404(model, id):
    rv = model.query.get(id)
    if not rv:
        abort(404)
    return rv


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
