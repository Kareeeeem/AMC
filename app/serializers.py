from flask import url_for
from marshmallow import (
    Schema as _Schema,
    SchemaOpts as _SchemaOpts,
    fields,
    validate, post_dump,
)


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta):
        _SchemaOpts.__init__(self, meta)
        self.route = getattr(meta, 'route', None)


class Schema(_Schema):
    OPTIONS_CLASS = SchemaOpts

    @post_dump(pass_original=True)
    def add_href(self, data, original):
        data['href'] = url_for(self.opts.route, id=original.id, _external=True)
        return data


class UserSchema(Schema):
    username = fields.Str(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))

    class Meta:
        strict = True
        route = 'api.users'
        additional = ('created_at', 'updated_at', 'last_login')
        load_only = ('password',)
        dump_only = ('created_at', 'updated_at')
