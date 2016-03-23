from marshmallow import ValidationError
from . import v1


@v1.errorhandler(ValidationError)
def validation_error(exception=None):
    status_code = 409 if 'conflicts' in exception.messages else 400
    return dict(errors=exception.messages), status_code
