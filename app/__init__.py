from flask import Flask, url_for

from config import config
from app import models, helpers

db = helpers.Database()
id_obfuscator = helpers.FlaskIntEncoder()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_loggers(app)
    app.response_class = helpers.HandleJSONReponse

    db.init_app(app)
    id_obfuscator.init_app(app)

    app.url_map.converters['id'] = id_obfuscator.id_converter

    @app.route('/')
    def index():
        users = db.session.query(models.User).all()
        link = '<div><a href="{}">{}</a></div>'
        # rv = ''.join([link.format(url_for('user', id=user.id), user.username)
        #               for user in users])
        rv = ''.join([link.format(url_for('user', id=user.id), user.username)
                      for user in users])
        return rv

    @app.route('/<id:id>')
    def user(id):
        return str(id)

    @app.teardown_appcontext
    def shutdown_session(exc=None):
        db.session.remove()

    @app.shell_context_processor
    def make_shellcontext():
        ctx = {'db': db}
        for subclass in models.Base.__subclasses__():
            ctx[subclass.__name__] = subclass
        return ctx

    return app
