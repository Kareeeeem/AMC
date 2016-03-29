import hashids

from flask import abort
from werkzeug.routing import BaseConverter


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
