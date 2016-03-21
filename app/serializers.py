from flask import url_for
from marshmallow import (
    Schema as _Schema,
    SchemaOpts as _SchemaOpts,
    fields,
    validate,
    # post_dump,
)


def get_url_arguments_from_obj(obj, **kwargs):
    return {k: getattr(obj, v) for k, v in kwargs.iteritems()}


def generate_url(route, **kwargs):
    return url_for(route, **kwargs)


class FlaskUrlField(fields.Field):
    '''A field that serializes the url of the resource.

    route: the flask route.
    route_args: a dictionairy mapping of the url keyword arguments and the object
    attributes that provide the value of said arguments.
    '''

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

    def __init__(self, nested, collection_route=None, collection_route_args=None,
                 *args, **kwargs):
        super(ExpandableNested, self).__init__(nested, *args, **kwargs)
        self.collection_route = collection_route
        self.collection_route_args = collection_route_args or {}

    def _serialize(self, value, attr, obj):
        parent_context = getattr(self.parent, 'context', {})
        expand = bool(attr in parent_context.get('expand', ''))

        if self.many and not expand:
            # return the collection route, no needs to serialize anything from
            # the nested collection.

            if not self.collection_route:
                raise AttributeError(self.ROUTE_ERROR)

            route_args = get_url_arguments_from_obj(obj, **self.collection_route_args)
            return generate_url(self.collection_route, **route_args)

        elif not self.many and not expand:
            # only serialize the href property of the nested item.
            self.only = 'href'

        return super(ExpandableNested, self)._serialize(value, attr, obj)


class SchemaOpts(_SchemaOpts):
    pass
    # def __init__(self, meta):
    #     _SchemaOpts.__init__(self, meta)
    #     self.route = getattr(meta, 'route', None)


class Schema(_Schema):
    pass
    # OPTIONS_CLASS = SchemaOpts

    # @post_dump(pass_original=True)
    # def add_href(self, data, original):
    #     if self.opts.route:
    #         data['href'] = url_for(self.opts.route, id=original.id)
    #         return data


class ExerciseSchema(Schema):
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    data = fields.Dict()
    href = FlaskUrlField(route='v1.exercises',
                         route_args={'id': 'id'},
                         dump_only=True)
    author = ExpandableNested('UserSchema', exclude=('exercises',))

    class Meta:
        strict = True
        additional = ('created_at', 'updated_at')
        dump_only = ('created_at', 'updated_at')


class UserSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    href = FlaskUrlField(route='v1.users',
                         route_args={'id': 'id'},
                         dump_only=True)
    exercises = ExpandableNested('ExerciseSchema',
                                 collection_route='v1.user_exercises',
                                 collection_route_args={'id': 'id'},
                                 exclude=('author',),
                                 dump_only=True,
                                 many=True,
                                 )

    class Meta:
        strict = True
        additional = ('created_at', 'updated_at', 'last_login')
        load_only = ('password',)
        dump_only = ('created_at', 'updated_at')
