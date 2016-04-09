from marshmallow import ValidationError
from sqlalchemy.exc import OperationalError

from app.lib import PaginationError, AuthorizationError
from app.models import MaxEditTimeExpiredError
from . import v1


@v1.errorhandler(OperationalError)
def db_connection_error(exception=None):
    return dict(errors=['Database connection error'], status_code=500), 500
    return {}, 500


@v1.errorhandler(MaxEditTimeExpiredError)
def max_edit_time_expired(exception=None):
    error = 'Maximum time for editing expired'
    status_code = 400
    return dict(errors=[error], status_code=status_code), status_code


@v1.errorhandler(ValidationError)
def validation_error(exception=None):
    status_code = 409 if 'conflicts' in exception.messages else 400
    error_dict = dict(message=exception.messages, status_code=status_code)
    return dict(errors=error_dict), status_code


@v1.errorhandler(PaginationError)
def pagination_error(exception=None):
    return exception.response, exception.status_code


@v1.errorhandler(AuthorizationError)
def unauthorized(exception=None):
    return exception.response, exception.status_code
