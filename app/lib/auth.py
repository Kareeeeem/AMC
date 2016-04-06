import functools

from flask import request
from werkzeug.local import LocalProxy


class Auth(object):
    '''AUthorization class that manages an OAuth authorization flow following
    this guide:
    https://stormpath.com/blog/the-ultimate-guide-to-mobile-api-security/
    '''
    def __init__(self, app=None):
        self.verify_token_callback = None
        self.verify_login_callback = None

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

            if (not username or
                    not password or
                    not self.verify_login_callback(username, password)):
                raise AuthorizationError

            return f(*args, **kwargs)
        return wrapper

    def get_user(self, f):
        '''Register a current_user callback as a werkzeug LocalProxy.'''
        self.current_user = LocalProxy(f)

    def authorize_with_token(self, auth_header):
        if request.method != 'OPTIONS':
            try:
                token_type, token = auth_header.split(' ')
            except ValueError:
                # malformed header
                raise AuthorizationError

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


class AuthorizationError(Exception):
    def __init__(self, message=None, status_code=401):
        self.message = message or "Unauthorized request"
        self.status_code = status_code
        self.response = dict(errors=dict(status=self.status_code, message=self.message))
        super(AuthorizationError, self).__init__(self.message)
