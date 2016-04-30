# import sys
import random
import os
import json

import click
from psycopg2.extras import NumericRange
from flask.cli import pass_script_info
from pgcli.main import PGCli

from app import db as db_, models
from scripts.cli import cli


def generate_users(amount=100):
    users = [models.User(username='user%s' % i,
                         email='email%s@gmail.com' % i,
                         password='00000000'
                         ) for i in xrange(amount)]
    db_.session.add_all(users)
    return users


def generate_exercises(users, amount=1000):
    categories = [
        models.Category(name=name) for name in
        'relaxatie concentratie associatie confrontatie'.split()
    ]
    categories.append(None)

    ranges = [NumericRange(0, 5), NumericRange(5, 15), NumericRange(15, None)]

    exercises = [models.Exercise(title='title%s' % i,
                                 description='desc%s' % i,
                                 author=random.choice(users),
                                 category=random.choice(categories),
                                 duration=random.choice(ranges),
                                 ) for i in xrange(amount)]

    db_.session.add_all(exercises)
    return exercises


def generate_ratings(users, exercises):
    db_.session.add_all(
        models.Rating(user=user, exercise=exercise, rating=random.choice((1, 2, 3, 4, 5)))
        for exercise in exercises
        for user in users
        # randomize the mount of ratings a bit. Every user should rate about
        # onr third of exercises.
        if random.choice([False, False, True])
    )


@cli.group(chain=True)
def db():
    '''Database operations.'''


@db.command()
@click.pass_context
def drop(ctx):
    '''Drop all database tables.'''
    models.Base.metadata.drop_all(db_.engine)
    click.echo('Dropped all tables')


@db.command()
@click.option('-d', is_flag=True, default=False)
@click.pass_context
def create(ctx, d):
    '''Optionally drop and create all database tables.'''
    if d:
        ctx.invoke(drop)
    models.Base.metadata.create_all(db_.engine)
    click.echo('Created all tables')


@db.command()
@click.pass_obj
def fill(obj):
    useramount = 10
    exerciseamount = 100
    users = generate_users(amount=useramount)
    exercises = generate_exercises(users, amount=exerciseamount)
    generate_ratings(users, exercises[:exerciseamount / 2])
    users[0].favorite_exercises = exercises[:10]

    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(basedir, 'amisos.json')) as amisos_json:
        data = json.load(amisos_json)
        amisos = models.Questionnaire(**data)
        db_.session.add(amisos)

    db_.session.commit()


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
