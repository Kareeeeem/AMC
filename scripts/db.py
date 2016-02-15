import os

import click
from flask.cli import pass_script_info
from pgcli.main import PGCli

from scripts.cli import cli


@cli.group(chain=True)
@click.pass_context
def db(ctx):
    '''Database operations.'''
    from app import models, db
    ctx.obj = dict(models=models, db=db)


@db.command()
@click.pass_obj
def create(obj):
    '''Create all database tables.'''
    obj['models'].Base.metadata.create_all(obj['db'].engine)
    # session = obj['db'].session
    # session.add(obj['models'].Token(type='revoked'))
    # session.commit()


@db.command()
@click.pass_obj
def user(obj):
    User = obj['models'].User
    db = obj['db']
    u = User(username='kareem', email='kareeeeem@gmail.com', password='0000')
    db.session.add(u)
    db.session.commit()


@db.command()
@click.pass_obj
def drop(obj):
    '''Drop all database tables.'''
    obj['models'].Base.metadata.drop_all(obj['db'].engine)


@cli.command()
@click.option('--pgclirc',
              default=os.path.expanduser('~/.config/pgcli/config'),
              envvar='PGCLIRC', help='Location of pgclirc file.')
@pass_script_info
def pgcli(info, pgclirc):
    '''Start a pgcli session.'''
    from flask.globals import _app_ctx_stack
    app = _app_ctx_stack.top.app
    pgcli = PGCli(pgclirc_file=pgclirc)
    pgcli.connect_uri(app.config['SQLALCHEMY_DATABASE_URI'])
    pgcli.run_cli()
