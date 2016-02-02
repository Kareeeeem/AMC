import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from app import models
from config import config as configurations

Session = sessionmaker()


@pytest.yield_fixture(scope='session')
def config(request):
    config = configurations['testing']
    yield config


@pytest.yield_fixture(scope='session')
def engine(config, request):
    config = configurations['testing']
    engine = create_engine(config.DATABASE_URI, convert_unicode=True)
    models.Base.metadata.create_all(engine)
    yield engine
    models.Base.metadata.drop_all(engine)


@pytest.yield_fixture(scope='function')
def session(engine, request):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()
