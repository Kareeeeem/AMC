from flask import Flask

from config import config
from app import lib
from models import db

auth = lib.Auth()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.response_class = lib.HandleJSONReponse

    config[config_name].init_loggers(app)

    app.url_map.converters['hashid'] = lib.HashIDConverter.with_salt(
        app.config.get('HASHID_SALT', '')
    )

    db.init_app(app)

    from app.api.v1 import auth
    app.register_blueprint(auth.bp)

    return app
