import pytest  # noqa

from app.lib import with_app_config


# the tests inside the application context are here
# ./test_with_app/test_with_config.py


def test_function_without_app():
    @with_app_config('KEY')
    def foo(KEY='NOKEY'):
        return KEY

    assert foo() == 'NOKEY'


def test_class_without_app():
    @with_app_config('KEY')
    class Foo(object):
        KEY = 'NOKEY'

    assert Foo().KEY == 'NOKEY'


def test_class_without_app_raises():
    @with_app_config('KEY')
    class Foo(object):
        pass

    with pytest.raises(RuntimeError):
        Foo.KEY


def test_class_instance_without_app_raises():
    @with_app_config('KEY')
    class Foo(object):
        pass

    with pytest.raises(RuntimeError):
        Foo.KEY
