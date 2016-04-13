from marshmallow import fields, validate, validates_schema

from meta import Schema
from fields import HashIDField, FlaskUrlField, ExpandableNested
from validators import validate_unique

from app import models
from app.lib import parse_query_params


class Serializer(object):
    def __init__(self, schema, request):
        self.schema = schema
        self.request = request
        self._context = {}

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    def get_expand(self):
        return parse_query_params(self.request.args, key='expand')

    def dump_page(self, page, items=None, **kwargs):
        schema = self.schema(page=page,
                             context=self.context,
                             expand=self.get_expand(),
                             **kwargs)
        if items:
            # the caller wants a bit more control over what he passes in.
            # Perhaps he ran some postprocessing on the items stored in page.
            return schema.dump(items, many=True).data

        return schema.dump(page.items, many=True).data

    def dump(self, obj, **kwargs):
        schema = self.schema(context=self.context,
                             expand=self.get_expand(),
                             **kwargs)
        return schema.dump(obj).data

    def load(self, **kwargs):
        schema = self.schema(context=self.context, **kwargs)
        return schema.load(self.request.get_json()).data


class ExerciseSchema(Schema):
    id = HashIDField()
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    data = fields.Dict()
    href = FlaskUrlField(route='v1.get_exercise',
                         route_args={'id': 'id'},
                         dump_only=True)
    author = ExpandableNested('UserSchema')

    favorited = fields.Bool()
    allow_edit = fields.Bool()

    class Meta:
        additional = ('created_at', 'updated_at')
        dump_only = ('created_at', 'updated_at', 'favorited', 'id')


class UserSchema(Schema):
    id = HashIDField(dump_only=True)
    username = fields.Str(required=True)

    href = FlaskUrlField(
        route='v1.get_user',
        route_args={'id': 'id'},
        dump_only=True)

    authored_exercises = ExpandableNested(
        'ExerciseSchema',
        collection_route='v1.get_user_exercises',
        route_arg_keys={'id': 'id'},
        exclude=('author',),
        dump_only=True,
        many=True,
    )


class ProfileSchema(UserSchema):
    email = fields.Email()
    password = fields.Str(required=True, validate=validate.Length(min=8))
    favorite_exercises = ExpandableNested(
        'ExerciseSchema',
        collection_route='v1.get_user_favorites',
        route_arg_keys={'id': 'id'},
        dump_only=True,
        many=True,
    )

    @validates_schema
    def validate(self, data):
        return validate_unique(self, data, models.User)

    class Meta:
        load_only = ('password',)
        additional = ('created_at', 'updated_at', 'last_login')
        dump_only = ('created_at', 'updated_at', 'last_login')


class ActionSchema(Schema):
    FAVORITE = 'favorite'
    UNFAVORITE = 'unfavorite'

    id = HashIDField(required=True)
    action = fields.Str(
        required=True,
        validate=validate.OneOf([FAVORITE, UNFAVORITE],
                                error='Must be one of {choices}'))
