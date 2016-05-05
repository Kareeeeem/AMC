import json
import os

import pytest

from app import (
    create_app,
    db,
    models,
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


@pytest.yield_fixture(scope='function')
def amisos(session):
    basedir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(basedir, 'amisos.json')) as amisos_json:
        data = json.load(amisos_json)
        amisos = models.Questionnaire.create(session, data)
        session.add(amisos)
    session.commit()
    yield amisos


@pytest.yield_fixture(scope='function')
def exercise(user, session):
    exercise = models.Exercise(title='ex',
                               description='ex desc',
                               author=user)
    session.add(exercise)
    session.commit()
    yield exercise
