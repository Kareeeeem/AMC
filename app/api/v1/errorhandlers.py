from marshmallow import ValidationError

from app.lib import PaginationError, AuthorizationError
from . import v1


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
