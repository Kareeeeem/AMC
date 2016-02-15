import click
from flask.cli import FlaskGroup, script_info_option


def create_app(info):
    from app import create_app, db, models
    config = info.data.get('config') or 'default'
    app = create_app(config)

    @app.shell_context_processor
    def make_shellcontext():
        ctx = {'db': db}
        for subclass in models.Base.__subclasses__():
            ctx[subclass.__name__] = subclass
        return ctx

    return app


@click.group(cls=FlaskGroup, create_app=create_app)
@script_info_option('--config', script_info_key='config')
def cli(**params):
    '''This is an entry point for scripts that require the app context.
    '''

import scripts.flask_app  # noqa
import scripts.db  # noqa
