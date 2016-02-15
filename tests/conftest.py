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
    db.session.configure(bind=connection)
    yield db.session
    db.session.remove()
    transaction.rollback()


@pytest.yield_fixture(scope='function')
def user(session):
    user = models.User(
        username='Kareem',
        password='0000',
        email='kareem@gmail.com',
    )
    session.add(user)
    session.commit()
    yield user
