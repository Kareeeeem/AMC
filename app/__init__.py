from flask import Flask

from app import lib
from config import config
from models import db

auth = lib.Auth()


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.response_class = lib.HandleJSONReponse

    config[config_name].init_loggers(app)

    hashid = lib.HashIDConverter.with_salt(app.config.get('HASHID_SALT', ''))
    app.url_map.converters['hashid'] = hashid

    db.init_app(app)
    auth.init_app(app)

    # API v1
    from app.api import v1
    app.register_blueprint(v1.v1, url_prefix='/v1')

    return app
