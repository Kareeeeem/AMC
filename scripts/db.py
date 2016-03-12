# import sys
import os
import json

import click
from flask.cli import pass_script_info
from pgcli.main import PGCli

from scripts.cli import cli


def get_db_and_models():
    from app import db, models
    return db, models


@cli.group(chain=True)
def db():
    '''Database operations.'''


@db.command()
@click.pass_context
def drop(ctx):
    '''Drop all database tables.'''
    db, models = get_db_and_models()
    models.Base.metadata.drop_all(db.engine)
    click.echo('Dropped all tables')


@db.command()
@click.option('-d', is_flag=True, default=False)
@click.pass_context
def create(ctx, d):
    '''Optionally drop and create all database tables.'''
    db, models = get_db_and_models()
    if d:
        ctx.invoke(drop)
    models.Base.metadata.create_all(db.engine)
    click.echo('Created all tables')


@db.command()
@click.pass_obj
def fill(obj):
    db, models = get_db_and_models()
    user = models.User(username='kareem',
                       email='kareeeeem@gmail.com',
                       password='0000')
    db.session.add(user)
    db.session.add(models.Exercise(title='first',
                                   description='first desc',
                                   author=user))

    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(basedir, 'amisos.json')) as amisos_json:
        data = json.load(amisos_json)
        amisos = models.Questionnaire(**data)
        db.session.add(amisos)

    exercise = models.Exercise(
        title='een nieuwe oefening',
        description='deze oefening is behulpzaam voor het onderhouden van uw mentale gezondheid. dit is bewezen door studies.')

    db.session.add(exercise)

    db.session.commit()


@db.command()
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
