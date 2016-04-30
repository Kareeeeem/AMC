import json


user_data = dict(
    username='kareem',
    password='12345678',
    email='kareem@gmail.com',
)

user_data2 = dict(
    username='kareem2',
    password='12345678',
    email='kareem2@gmail.com',
)


def register(app, **kwargs):
    with app.test_client() as client:
        rv = client.post('/v1/users',
                         data=json.dumps(kwargs),
                         content_type='application/json',
                         )
    return rv


def get_token(app, username, password):
    with app.test_client() as client:
        rv = client.post('/v1/login', data=dict(
            grant_type='password',
            username=username,
            password=password
        ))
    return json.loads(rv.data)['access_token']


def test_registration(app, session):
    rv = register(app, **user_data)
    assert rv.status_code == 201


def test_get_user(app, session):
    resp = register(app, **user_data)

    with app.test_client() as client:
        rv = client.get(resp.headers['Location'])
    assert rv.status_code == 200


def test_put_other_user(app, session):
    register(app, **user_data)
    resp2 = register(app, **user_data2)
    jwt = get_token(app, user_data['username'], user_data['password'])

    with app.test_client() as client:
        rv = client.put(resp2.headers['Location'],
                        data=json.dumps(dict(username='x', email='h@h.nl')),
                        content_type='application/json',
                        headers=dict(Authorization='Bearer {}'.format(jwt))
                        )
    assert rv.status_code == 401


def test_get_user_not_found(app, session):
    register(app, **user_data)
    jwt = get_token(app, user_data['username'], user_data['password'])

    with app.test_client() as client:
        rv = client.get('/v1/users/45',
                        content_type='application/json',
                        headers=dict(Authorization='Bearer {}'.format(jwt)))
    assert rv.status_code == 404 and rv.content_type == 'application/json'


def test_put_user(app, session):
    resp = register(app, **user_data)
    user = json.loads(resp.data)

    jwt = get_token(app, user_data['username'], user_data['password'])

    user['username'] = 'hajar'
    with app.test_client() as client:
        rv = client.put(resp.headers['Location'],
                        data=json.dumps(user),
                        content_type='application/json',
                        headers=dict(Authorization='Bearer {}'.format(jwt)))
    assert rv.status_code == 200 and json.loads(rv.data)['data']['username'] == 'hajar'


def test_delete_user(app, session):
    resp = register(app, **user_data)
    jwt = get_token(app, user_data['username'], user_data['password'])
    with app.test_client() as client:
        rv = client.delete(resp.headers['Location'],
                           headers=dict(Authorization='Bearer {}'.format(jwt)))
    assert rv.status_code == 204
