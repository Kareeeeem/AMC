from flask import Flask

from config import config
from app import lib


db = lib.Database()
hashid = lib.FlaskIntEncoder()
auth = lib.Auth()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.response_class = lib.HandleJSONReponse

    config[config_name].init_loggers(app)

    db.init_app(app)
    hashid.init_app(app)
    app.url_map.converters['id'] = hashid.id_converter

    from app.api.v1 import auth
    app.register_blueprint(auth.bp)

    @app.teardown_appcontext
    def shutdown_session(exc=None):
        db.session.remove()

    return app
