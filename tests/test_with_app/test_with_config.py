import pytest  # noqa

from app.lib import with_app_config

# the tests outside of application context (to test fallbacks) are here:
# ./test_without_app/test_with_config.py


def test_function_with_app(app):
    app.config['KEY'] = 'VALUE'

    @with_app_config('KEY')
    def foo(KEY='NOVALUE'):
        return KEY

    assert foo() == 'VALUE'


def test_class_app(app):
    app.config['KEY'] = 'VALUE'

    @with_app_config('KEY')
    class Foo(object):
        KEY = 'NOVALUE'

    assert Foo().KEY == 'VALUE'
