import json


def login(app, username, password):
    with app.test_client() as client:
        rv = client.post('/v1/login', data=dict(
            grant_type='password',
            username=username,
            password=password
        ))
    return rv


def test_login(app, user):
    rv = login(app, 'kareem', '0000')
    assert rv.status_code == 200


def test_login_fail(app, user):
    rv = login(app, 'kareem', 'badpassword')
    assert rv.status_code == 401


def test_login_fail2(app, user):
    with app.test_client() as client:
        rv = client.post('/v1/login', data=dict(
            username='kareem',
            password='0000'
        ))
    assert rv.status_code == 401


def test_login_fail3(app, user):
    with app.test_client() as client:
        rv = client.post('/v1/login', data=dict(
            grant_type='password',
            password='0000'
        ))
    assert rv.status_code == 401


def test_login_fail4(app, user):
    with app.test_client() as client:
        rv = client.post('/v1/login', data=dict(
            grant_type='password',
            username='kareem',
        ))
    assert rv.status_code == 401


def test_case_insensitive_login(app, user):
    rv = login(app, 'kAreEm', '0000')
    assert rv.status_code == 200


def test_email_login(app, user):
    rv = login(app, 'kareem@gmail.com', '0000')
    assert rv.status_code == 200


def test_jwt(app, user):
    rv = login(app, 'kareem@gmail.com', '0000')
    jwt_claims = user.verify_auth_token(json.loads(rv.data)['access_token'])
    assert jwt_claims['id'] == user.id


def test_use_token_for_auth(app, user):
    rv = login(app, 'kareem@gmail.com', '0000')
    jwt = json.loads(rv.data)['access_token']
    location = rv.headers['Location']
    with app.test_client() as client:
        rv = client.get(location, headers=dict(
            Authorization='Bearer {}'.format(jwt)))
    assert rv.status_code == 200
