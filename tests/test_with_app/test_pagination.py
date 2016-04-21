import pytest

from app.lib import Pagination, PaginationError
from app.models import User
from app.serializers import UserSchema
from app.serializers import Serializer

from werkzeug.datastructures import MultiDict


# some fake classes that implement the values the pagination class
# will request from it.
class FakeUrlRule(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint or 'v1.get_exercises'


class FakeRequest(object):
    def __init__(self, args=None, view_args=None, endpoint=None):
        self.args = MultiDict(args) if args else MultiDict()
        self.view_args = view_args or {}
        self.url_rule = FakeUrlRule(endpoint)


def test_empty_page(session):
    query = User.query
    page = Pagination(FakeRequest(), query)
    result = Serializer(UserSchema).dump_page(page)
    assert result['items'] == []


def test_page_doesnt_exist(session):
    query = User.query
    with pytest.raises(PaginationError):
        Pagination(FakeRequest(args={'page': 2}), query)


def test_many_pages(session):
    users = [User(username='user%s' % i,
                  email='email%s@gmail.com' % i,
                  password='00000000'
                  ) for i in xrange(10)]
    session.add_all(users)
    session.commit()
    query = User.query
    request = FakeRequest(args={'per_page': 2})
    page = Pagination(request, query)
    result = Serializer(UserSchema).dump_page(page)
    assert len(result['items']) == 2
