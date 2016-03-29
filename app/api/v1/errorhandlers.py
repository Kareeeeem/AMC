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
    return dict(errors=exception.response), 400


@v1.errorhandler(404)
def not_found_error(exception=None):
    error = dict(status_code=404, message='Resource not found')
    return dict(errors=error), 404


@v1.errorhandler(AuthorizationError)
def unauthorized(exception=None):
    return dict(errors=exception.response), exception.status_code
