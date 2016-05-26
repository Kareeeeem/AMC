import bleach
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


def expandable(obj, attribute, expand, nested, route, route_kwargs, **kwargs):
    '''Generate an external url if attribute is not in expand, otherwise
    serialize the expandable attribute.'''

    if attribute not in expand:
        url = make_url(route, **{arg: getattr(obj, attribute) for arg, attribute
                                 in route_kwargs.iteritems()})
        return url

    field = fields.Nested(nested, **kwargs)
    return field.serialize(attribute, obj)


class Serializer(object):
    def __init__(self, schema, query_params=None, context=None):
        self.schema = schema
        self.query_params = query_params
        self._context = context or {}

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
    def bleach(self, data):
        allowed_attrs = {
            'a': ['href', 'rel'],
            'img': ['src', 'alt']
        }
        allowed_tags = ['a', 'img', 'br', 'em', 'strong']
        description = data.pop('description', '')
        description = bleach.clean(description,
                                   tags=allowed_tags,
                                   attributes=allowed_attrs)
        print description
        description = bleach.linkify(description)
        data['description'] = description
        return data

    @post_load
    def set_category(self, data):
        category_name = data.pop('category_name', None)
        if category_name:
            data['category'] = models.Category.query.\
                filter_by(name=category_name).first()
        return data

    @validates('category')
    def validate_category(self, value):
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

    authored_exercises = fields.Method('get_authored', dump_only=True)

    def get_authored(self, obj):
        return expandable(obj,
                          attribute='authored_exercises',
                          expand=self.expand,
                          nested=ExerciseSchema,
                          route='v1.get_exercises',
                          route_kwargs={'author': 'username'},
                          many=True)

    class Meta:
        wrap = True
        meta = 'id', 'href',
        related = 'authored_exercises', 'favorite_exercises',


class ProfileSchema(UserSchema):
    email = fields.Email()
    password = fields.Str(required=True, validate=validate.Length(min=8))

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
    count = fields.Integer()

    @staticmethod
    def validate_rating(value):
        if value < 1 or value > 5:
            raise ValidationError('Valid ratings are from 1 to 5.')

    @validates('fun')
    def validate_fun(self, value):
        return self.validate_rating(value)

    @validates('clear')
    def validate_clear(self, value):
        return self.validate_rating(value)

    @validates('effective')
    def validate_effective(self, value):
        return self.validate_rating(value)


class OptionSchema(Schema):
    value = fields.Integer(required=True)
    text = fields.Str(required=True)


class QuestionSchema(Schema):
    id = HashIDField(dump_only=True)
    text = fields.Str(required=True)
    ordinal = fields.Integer(required=True)
    options = fields.Nested(OptionSchema, many=True)


class ScoreSchema(Schema):
    range = fields.Nested(NumericRangeSchema, required=True)
    name = fields.Str(required=True)


class QuestionnaireSchema(Schema):
    id = HashIDField(dump_only=True)
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    questions = fields.Nested(QuestionSchema, many=True)
    possible_scores = fields.Nested(ScoreSchema, many=True)
    href = fields.Function(lambda obj: make_url('v1.get_questionnaire', id=obj.id),
                           dump_only=True)
    responses = fields.Method('get_responses', dump_only=True)
    max_score = fields.Method('get_max_score', dump_only=True)

    def get_max_score(self, obj):
        sum = 0
        for question in obj.questions:
            sum += max(o.value for o in question.options)
        return sum

    def get_responses(self, obj):
        return expandable(obj,
                          attribute='responses',
                          expand=self.expand,
                          nested=QuestionnaireResponseSchema,
                          route='v1.get_responses',
                          route_kwargs={'id': 'id'},
                          many=True,
                          exclude=['questionnaire']
                          )

    class Meta:
        wrap = True
        meta = 'id', 'href', 'max_score'
        related = 'responses',


class ChoiceSchema(Schema):
    value = fields.Integer(required=True)
    question_id = HashIDField(required=True)


class QuestionnaireResponseSchema(Schema):
    choices = fields.Nested(ChoiceSchema, many=True, required=True)
    questionnaire = fields.Method('get_questionnaire', dump_only=True)
    total = fields.Function(lambda obj: sum(c.value for c in obj.choices),
                            dump_only=True)

    def get_questionnaire(self, obj):
        return expandable(obj,
                          attribute='questionnaire',
                          expand=self.expand,
                          nested=QuestionnaireSchema,
                          route='v1.get_questionnaire',
                          route_kwargs={'id': 'questionnaire_id'},
                          )
    score = fields.Nested(ScoreSchema)

    class Meta:
        wrap = True
        dump_only = 'questionnaire', 'score'
        meta = 'score', 'total'
        related = 'questionnaire',

    @validates('choices')
    def validate_category(self, value):
        questionnaire = self.context.get('questionnaire')
        original_question_ids = [question.id
                                 for question in questionnaire.questions]
        given_question_ids = [choice['question_id'] for choice in value]
        if set(original_question_ids) ^ set(given_question_ids):
            raise ValidationError('Response is missing questions.')

        # TODO valid values for choices


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
