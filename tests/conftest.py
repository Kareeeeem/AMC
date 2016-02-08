import pytest

from app import (
    create_app,
    models,
    db,
)


@pytest.yield_fixture(scope='session')
def app(request):
    app = create_app('testing')
    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


@pytest.yield_fixture(scope='session')
def connection(app, request):
    models.Base.metadata.create_all(db.engine)
    connection = db.engine.connect()
    yield connection
    connection.close()
    models.Base.metadata.drop_all(db.engine)


@pytest.yield_fixture(scope='function')
def session(connection, request):
    transaction = connection.begin()

    # get at the session factory to create a new non-scoped session
    # bound to the connection.
    Session = db.session.session_factory
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
