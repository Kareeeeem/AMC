from flask import url_for
from marshmallow import (
    Schema as _Schema,
    SchemaOpts as _SchemaOpts,
    fields,
    validate,
    # post_dump,
)


class FlaskUrlField(fields.Field):
    '''A field that serializes the url of the resource.

    route: the flask route.
    url_args: a dictionairy mapping of the url keyword arguments and the object
    attributes that provide the value of said arguments.
    '''

    _CHECK_ATTRIBUTE = False

    def __init__(self, route, url_args=None, *args, **kwargs):
        super(FlaskUrlField, self).__init__(*args, **kwargs)
        self.route = route
        self.url_args = url_args or {}

    def _serialize(self, value, attr, obj):
        url_args = {k: getattr(obj, v) for k, v in self.url_args.iteritems()}
        return url_for(self.route, **url_args)


class Nested(fields.Nested):
    '''A nested subclass that checks the context if the nested element should
    be expanded. And otherwise it should only serialize the href attribute.
    '''

    def _serialize(self, value, attr, obj):
        parent_context = getattr(self.parent, 'context', {})
        if attr not in parent_context.get('expand', ''):
            self.only = 'href'
        return super(Nested, self)._serialize(value, attr, obj)


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
                         url_args={'id': 'id'},
                         dump_only=True)

    class Meta:
        strict = True
        additional = ('created_at', 'updated_at')
        dump_only = ('created_at', 'updated_at')


class UserSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    href = FlaskUrlField(route='v1.users',
                         url_args={'id': 'id'},
                         dump_only=True)
    exercises = Nested('ExerciseSchema', many=True)

    class Meta:
        strict = True
        additional = ('created_at', 'updated_at', 'last_login')
        load_only = ('password',)
        dump_only = ('created_at', 'updated_at')
