from flask import Blueprint

v1 = Blueprint('api', __name__)

from . import api, auth  # noqa
