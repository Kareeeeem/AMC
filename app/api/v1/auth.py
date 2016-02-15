from flask import Blueprint, request, abort, g
from sqlalchemy import or_

from app import models, db, auth

bp = Blueprint('auth', __name__, url_prefix='/v1/auth')

# The app follows the guidelines explained in this article.
# https://stormpath.com/blog/the-ultimate-guide-to-mobile-api-security/


# TODO return usefull errors

@bp.route('/test')
def index():
    return 'hello'


@auth.verify_token
def verify_token(token):
    '''Callback to be ran when a route is marked as login_required.
    '''
    data = models.User.verify_auth_token(token)
    if data:
        g.claims = data
        return True


@auth.error_handler
def reject_token():
    abort(401)


@bp.route('/login', methods=['POST'])
def login():
    '''The user will post his credentials here as form content.
    application/www-x-form-urlencoded, and the server will respond with a JWT.

    The required fields are: grant_type=password username=[USERNAMEOREMAIL]
    password=[PASSWORD]

    '''
    form = request.form

    if form.get('grant_type') != 'password':
        abort(400)

    username_or_email = form.get('username')
    password = form.get('password')
    # ilike operator for case insensitive match
    user = db.session.query(models.User).filter(
        or_(models.User.username.ilike(username_or_email),
            models.User.email.ilike(username_or_email))).first()

    if not user or not user.verify_password(password):
        abort(401)

    return user.generate_auth_token()


@bp.route('/logout', methods=['GET'])
@auth.login_required
def logout():
    return 'hello'
