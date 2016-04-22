from flask import url_for
from marshmallow import (
    fields,
    validate,
    validates_schema,
    validates,
    ValidationError,
)

from app import models, db
from app.lib import parse_query_params
from fields import HashIDField
from meta import Schema
from validators import validate_unique


def generate_url(route, **kwargs):
    return url_for(route, _external=True, **kwargs)


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
        return schema.dump(page.items, many=True).data

    def dump(self, obj, **kwargs):
        schema = self.schema(context=self.context,
                             expand=self.get_expand(),
                             **kwargs)
        return schema.dump(obj).data

    def load(self, json, **kwargs):
        schema = self.schema(context=self.context, **kwargs)
        return schema.load(json).data


class ExerciseSchema(Schema):
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    data = fields.Dict()
    category = fields.Str(required=True, attribute='category_name')

    @validates('category')
    def validate_category(self, value):
        print value
        categories = [c.name for c in
                      db.session.query(models.Category.name).all()]
        if value not in categories:
            msg = 'category must be one of: {}.'.format(', '.join(categories))
            raise ValidationError(msg)

    id = HashIDField(dump_only=True)
    favorited = fields.Bool(dump_only=True)
    avg_rating = fields.Decimal(places=2, dump_only=True)
    my_rating = fields.Integer(attribute='rating', dump_only=True)
    allow_edit = fields.Bool(dump_only=True)
    author = fields.Method('get_author', dump_only=True)
    href = fields.Function(lambda o: generate_url('v1.get_exercise', id=o.id),
                           dump_only=True)

    def get_author(self, obj):
        if 'author' not in self.expand:
            return generate_url('v1.get_user', id=obj.author_id)
        else:
            return fields.Nested(UserSchema).serialize('author', obj)

    class Meta:
        additional = ('created_at', 'updated_at')
        dump_only = ('created_at', 'updated_at')


class UserSchema(Schema):
    id = HashIDField(dump_only=True)
    username = fields.Str(required=True)
    authored_exercises = fields.Method('get_authored')
    href = fields.Function(lambda o: generate_url('v1.get_user', id=o.id))

    def get_authored(self, obj):
        if 'authored_exercises' not in self.expand:
            return generate_url('v1.get_exercises', author_id=obj.id)

        field = fields.Nested(ExerciseSchema, many=True)
        return field.serialize('authored_exercises', obj)

    class Meta:
        dump_only = ('authored_exercises',
                     'href',
                     )


class ProfileSchema(UserSchema):
    email = fields.Email()
    password = fields.Str(required=True, validate=validate.Length(min=8))
    favorite_exercises = fields.Method('get_favorites')
    href = fields.Function(lambda o: generate_url('v1.get_user', id=o.id))

    def get_favorites(self, obj):
        if 'favorite_exercises' not in self.expand:
            return generate_url('v1.get_exercises', favorited_by=obj.id)

        field = fields.Nested(ExerciseSchema, many=True)
        return field.serialize('favorite_exercises', obj)

    @validates_schema
    def validate(self, data):
        return validate_unique(self, data, models.User)

    class Meta:
        load_only = ('password',)
        additional = ('created_at',
                      'updated_at',
                      'last_login',
                      )
        dump_only = ('created_at',
                     'updated_at',
                     'last_login',
                     'favorite_exercises',
                     'authored_exercises',
                     'href',
                     )


class ActionSchema(Schema):
    UNFAVORITE = 'unfavorite'
    FAVORITE = 'favorite'

    id = HashIDField(required=True)
    action = fields.Str(
        required=True,
        validate=validate.OneOf([FAVORITE, UNFAVORITE],
                                error='Must be one of {choices}'))


class RatingSchema(Schema):
    rating = fields.Integer(required=True)

    @validates('rating')
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise ValidationError('Rating must be larger than zero and lower than 5')
