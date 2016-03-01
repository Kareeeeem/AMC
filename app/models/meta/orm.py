from flask import _app_ctx_stack

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm import sessionmaker, scoped_session, class_mapper


class _QueryProperty(object):
    '''When accessed it returns a query object attached to the model. Enabling
    querying models with: `Model.query.all()`
    it is syntastic sugar for: `db.session.query`.
    '''
    def __init__(self, db):
        self.db = db

    def __get__(self, instance, owner):
        try:
            mapper = class_mapper(owner)
            if mapper:
                return self.db.session.query(mapper)
        except UnmappedClassError:
            return None


class BaseModel(object):
    @declared_attr
    def __tablename__(cls):
        '''Set the table name to the lowercase version of the class name'''
        return cls.__name__.lower()

    query = None


class Database(object):
    '''A class that serves as the accesspoint for database operations using an
    SQLAlchemy scoped_session. It also sets up an obscure id function in the
    database.
    '''
    def __init__(self, app=None):
        self.engine = None
        self.session = None
        self.Base = self.make_declarative_base()

        if app:
            self.init_app(app)

    def make_declarative_base(self):
        Base = declarative_base(cls=BaseModel)
        Base.query = _QueryProperty(self)
        return Base

    def init_app(self, app):
        self.database_uri = app.config['SQLALCHEMY_DATABASE_URI']
        self.echo = app.config.get('SQLALCHEMY_ECHO', False)
        self.engine = self.create_engine()
        self.session = self.create_scoped_session()

        app.teardown_appcontext(lambda exc: self.session.remove())

    def create_engine(self):
        return create_engine(self.database_uri,
                             echo=self.echo,
                             convert_unicode=True)

    def create_scoped_session(self):
        return scoped_session(sessionmaker(bind=self.engine),
                              scopefunc=_app_ctx_stack.__ident_func__)


db = Database()
