from collections import namedtuple
from app.lib.utils import (
    setattr_and_return,
    merge_sqla_results,
    parse_query_params,
)

from werkzeug.datastructures import MultiDict


def test_setattr():
    class Foo(object):
        pass

    f = Foo()

    withx = setattr(f, 'x', 'x')
    withy = setattr_and_return(f, 'y', 'y')

    assert f.x == 'x' and f.y == 'y' and not withx and withy


def test_merge_results():
    class Foo(object):
        pass

    nt = namedtuple('nt', 'Foo x y')

    results = [nt(Foo(), 1, 2), nt(Foo(), 3, 4)]
    # the function returns a generator, for testing it's easier if it's a list
    merged = list(merge_sqla_results(results))

    assert len(merged) == len(results)
    assert type(merged[0]) == Foo and type(results[0]) == nt
    assert merged[0].x == 1 and merged[0].y == 2


def test_merge_results_without_named_tuple():
    class Foo(object):
        pass

    results = [Foo(), Foo(), Foo()]
    merged = list(merge_sqla_results(results))
    assert len(merged) == len(results)


def test_parse_query_params_list():
    md = MultiDict([('a', 'b'), ('a', 'c')])
    a = parse_query_params(md, key='a')
    assert a == ['b', 'c']


def test_parse_query_params_comma():
    md = MultiDict([('a', 'b,c')])
    a = parse_query_params(md, key='a')
    assert a == ['b', 'c']


def test_parse_query_params_combined():
    md = MultiDict([('a', 'b,c'), ('a', 'x')])
    a = parse_query_params(md, key='a')
    assert a == ['b', 'c', 'x']
