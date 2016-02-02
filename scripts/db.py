from contextlib import contextmanager

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from config import config as configurations


class Database(object):
    def __init__(self, database_uri, silent=False):
        self.engine = create_engine(database_uri,
                                    convert_unicode=True,
                                    echo=not silent)
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session_context(self):
        session = self.Session()
        yield session
        session.close()


@click.group(chain=True)
@click.option('--silent', '-s', is_flag=True, help='Supress SQLAlchemy echo.')
@click.option('--config', '-c', default='development')
@click.pass_context
def cli(ctx, silent, config):
    '''Entry point for database scripts.'''
    config = configurations[config]
    config.init_loggers()
    ctx.obj = Database(config.DATABASE_URI, silent=silent)


@cli.command()
@click.pass_obj
def create(db):
    '''Create all tables.'''
    Base.metadata.create_all(db.engine)


@cli.command()
@click.pass_obj
def drop(db):
    '''Drop all tables.'''
    Base.metadata.drop_all(db.engine)
