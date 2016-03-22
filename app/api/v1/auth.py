from flask import g
from sqlalchemy import or_

from app import auth, db, models
from app.lib import get_location_header

from . import v1


@auth.verify_token
def verify_token(token):
    '''Callback to be ran when a route is marked as token_required.
    '''
    data = models.User.verify_auth_token(token)
    if data:
        g.claims = data
        g.current_user = models.User.query.get(data['id'])
        return True


def find_user_with_login(username_or_email, password):
    '''Find a user with the login information, username and email are matched
    case insensitive.
    '''
    filter_clause = or_(models.User.username.ilike(username_or_email),
                        models.User.email.ilike(username_or_email))
    return db.session.query(models.User).filter(filter_clause).first()


@auth.verify_login
def verify_login(username_or_email, password):
    '''Callback to be ran when a route is marked as login_required.
    '''
    user = find_user_with_login(username_or_email, password)
    if user and user.password == password:
        g.user = user
        return True


@v1.route('/login', methods=['POST'])
@auth.login_required
def login():
    '''The user will post his credentials here as form content and the server
    will respond with a JWT.

    Content-Type: application/www-x-form-urlencoded

    The required fields are:
        grant_type='password'
        username=[USERNAMEOREMAIL]
        password=[PASSWORD]
    '''
    rv = g.user.login(db.session)
    return rv, 303, get_location_header('.get_user', id=g.user.id)
