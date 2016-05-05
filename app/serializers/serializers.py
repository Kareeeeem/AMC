from psycopg2.extras import NumericRange
from marshmallow import (
    post_load,
    fields,
    validate,
    validates_schema,
    validates,
    ValidationError,
)

from app import models
from app.lib import parse_query_params, make_url
from fields import HashIDField
from meta import Schema
from validators import validate_unique


def expandable(obj, attribute, expand, nested, route, route_kwargs, many=False):
    '''Generate an external url if attribute is not in expand, otherwise
    serialize the expandable attribute.'''

    if attribute not in expand:
        url = make_url(route, **{arg: getattr(obj, attribute) for arg, attribute
                                 in route_kwargs.iteritems()})
        return url

    field = fields.Nested(nested, many=many)
    return field.serialize(attribute, obj)


class Serializer(object):
    def __init__(self, schema, query_params=None):
        self.schema = schema
        self.query_params = query_params
        self._context = {}

    @property
    def context(self):
        return self._context

    @context.setter
    def context(self, context):
        self._context = context

    def get_expand(self):
        if self.query_params:
            return parse_query_params(self.query_params, key='expand')

    def dump_page(self, page, **kwargs):
        schema = self.schema(page=page,
                             context=self.context,
                             expand=self.get_expand(),
                             **kwargs)
        dumped_page = PaginationSchema().dump(page).data
        dumped_items = schema.dump(page.items, many=True).data
        return dict(dumped_page, items=dumped_items)

    def dump(self, obj, **kwargs):
        schema = self.schema(context=self.context,
                             expand=self.get_expand(),
                             **kwargs)
        return schema.dump(obj).data

    def load(self, json, **kwargs):
        schema = self.schema(context=self.context, **kwargs)
        return schema.load(json).data


class NumericRangeSchema(Schema):
    min = fields.Integer(required=True, attribute='lower')
    max = fields.Integer(attribute='upper')

    @post_load
    def create_numeric_range(self, data):
        return NumericRange(data.get('lower', 0), data.get('upper', None))


class ExerciseSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=4))
    description = fields.Str(required=True, validate=validate.Length(min=10))
    json = fields.Dict()
    group_exercise = fields.Boolean()
    private_exercise = fields.Boolean()
    difficulty = fields.Integer()
    category = fields.Str(attribute='category_name')
    duration = fields.Nested(NumericRangeSchema, required=True)

    id = HashIDField(dump_only=True)
    favorited = fields.Bool(dump_only=True)
    edit_allowed = fields.Bool(dump_only=True)
    author = fields.Method('get_author', dump_only=True)
    href = fields.Function(lambda obj: make_url('v1.get_exercise', id=obj.id),
                           dump_only=True)
    rating = fields.Function(lambda obj: make_url('v1.rate_exercise', id=obj.id),
                             dump_only=True)

    popularity = fields.Float(dump_only=True)
    user_rating = fields.Nested('RatingSchema', dump_only=True)
    average_rating = fields.Nested('RatingSchema', dump_only=True)

    @post_load
    def set_category(self, data):
        category_name = data.pop('category_name', None)
        if category_name:
            data['category'] = models.Category.query.\
                filter_by(name=category_name).first()
        return data

    @validates('category')
    def validate_category(self, value):
        if value:
            categories = [c.name for c in models.Category.query.all()]
            if value not in categories:
                msg = 'category must be one of: {}.'.format(', '.join(categories))
                raise ValidationError(msg)

    def get_author(self, obj):
        return expandable(obj,
                          attribute='author',
                          expand=self.expand,
                          nested=UserSchema,
                          route='v1.get_user',
                          route_kwargs={'id': 'author_id'})

    class Meta:
        wrap = True
        additional = 'created_at', 'updated_at'
        dump_only = 'created_at', 'updated_at'
        related = 'author', 'rating',
        meta = 'id', 'average_rating', 'user_rating', 'href', 'favorited', \
            'edit_allowed', 'created_at', 'updated_at', 'popularity', \
            'avg_fun_rating', 'avg_effective_rating', 'avg_clear_rating', \
            'avg_rating'


class UserSchema(Schema):
    id = HashIDField(dump_only=True)
    username = fields.Str(required=True)
    authored_exercises = fields.Method('get_authored', dump_only=True)
    href = fields.Function(lambda obj: make_url('v1.get_user', id=obj.id),
                           dump_only=True)

    def get_authored(self, obj):
        return expandable(obj,
                          attribute='authored_exercises',
                          expand=self.expand,
                          nested=ExerciseSchema,
                          route='v1.get_exercises',
                          route_kwargs={'author_id': 'id'},
                          many=True)

    class Meta:
        wrap = True
        meta = 'id', 'href',
        related = 'authored_exercises',


class ProfileSchema(UserSchema):
    email = fields.Email()
    password = fields.Str(required=True, validate=validate.Length(min=8))
    href = fields.Function(lambda obj: make_url('v1.get_user', id=obj.id),
                           dump_only=True)
    favorite_exercises = fields.Method('get_favorites', dump_only=True)

    def get_favorites(self, obj):
        return expandable(obj,
                          attribute='favorite_exercises',
                          expand=self.expand,
                          nested=ExerciseSchema,
                          route='v1.get_exercises',
                          route_kwargs={'favorited_by': 'id'},
                          many=True)

    @validates_schema
    def validate(self, data):
        return validate_unique(self, data, models.User)

    class Meta:
        wrap = True
        load_only = 'password',
        additional = 'created_at', 'updated_at', 'last_login',
        dump_only = 'created_at', 'updated_at', 'last_login',
        meta = 'id', 'href', 'created_at', 'updated_at', 'last_login',
        related = 'authored_exercises', 'favorite_exercises',


class ActionSchema(Schema):
    UNFAVORITE = 'unfavorite'
    FAVORITE = 'favorite'

    id = HashIDField(required=True)
    action = fields.Str(
        required=True,
        validate=validate.OneOf([FAVORITE, UNFAVORITE],
                                error='Must be one of {choices}'))


class RatingSchema(Schema):
    rating = fields.Float(required=True, dump_only=True)
    fun = fields.Integer(required=True)
    clear = fields.Integer(required=True)
    effective = fields.Integer(required=True)

    @validates('clear')
    @validates('fun')
    @validates('effective')
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise ValidationError('Rating must be larger than zero and lower than 5')


class PaginationSchema(Schema):
    page = fields.Integer()
    pages = fields.Integer()
    per_page = fields.Integer()

    total = fields.Integer(attribute='total_count')
    next = fields.Url(attribute='next_page_url')
    prev = fields.Url(attribute='prev_page_url')
    first = fields.Url(attribute='first_page_url')
    last = fields.Url(attribute='last_page_url')
    current = fields.Url(attribute='current_page_url')
