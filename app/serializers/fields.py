from marshmallow import fields, ValidationError
from flask import url_for
from app import hashid


def get_url_arguments_from_obj(obj, **kwargs):
    return {k: getattr(obj, v) for k, v in kwargs.iteritems()}


def generate_url(route, **kwargs):
    return url_for(route, _external=True, **kwargs)


class FlaskUrlField(fields.Field):
    '''A field that serializes the url of the resource.

    route: the flask route.
    route_args: a dictionairy mapping of the url keyword arguments and the object
    attributes that provide the value of said arguments.
    '''

    # This attribute is not pulled from the object.
    _CHECK_ATTRIBUTE = False

    def __init__(self, route, route_args=None, *args, **kwargs):
        super(FlaskUrlField, self).__init__(*args, **kwargs)
        self.route = route
        self.route_args = route_args or {}

    def _serialize(self, value, attr, obj):
        route_args = get_url_arguments_from_obj(obj, **self.route_args)
        return generate_url(self.route, **route_args)


class ExpandableNested(fields.Nested):
    '''A nested subclass that checks the context if the nested element should
    be expanded. And otherwise it should only serialize the href attribute.
    '''
    ROUTE_ERROR = 'ExpandableNested with many=True requires a collection route'

    def __init__(self, nested, collection_route=None, route_arg_keys=None,
                 *args, **kwargs):

        super(ExpandableNested, self).__init__(nested, *args, **kwargs)

        if self.many and not collection_route:
            raise AttributeError(self.ROUTE_ERROR)

        self.collection_route = collection_route
        self.route_arg_keys = route_arg_keys or {}

    def _serialize(self, value, attr, obj):
        expand = bool(attr in self.parent.expand)

        if self.many and not expand:
            # return the collection route, no needs to serialize anything from
            # the nested collection.
            route_args = get_url_arguments_from_obj(obj, **self.route_arg_keys)
            return generate_url(self.collection_route, **route_args)

        elif not self.many and not expand:
            # only serialize the href property of the nested item.

            # FIXME this actually causes a bug when wrapping data in a
            # post_dump hook. So don't do that just yet untill I figure it out.
            # It's fine when self.only is set in __init__ but we only want it
            # set in this case. And we don't know about `expand` untill the
            # parent is initialized.
            self.only = 'href'

        return super(ExpandableNested, self)._serialize(value, attr, obj)


class HashIDField(fields.Field):
    def _serialize(self, value, attr, obj):
        if value:
            return hashid.encode(value)

    def _deserialize(self, value, attr, data):
        if value:
            try:
                return hashid.decode(value)[0]
            except IndexError:
                raise ValidationError('Invalid id')
