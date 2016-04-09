from flask import url_for
from marshmallow import (
    Schema as _Schema,
    SchemaOpts as _SchemaOpts,
    fields,
    validate,
    ValidationError,
    validates_schema,
    post_dump,
)
from sqlalchemy import or_

from app import models, hashid


def validate_unique(schema, data, model):
    '''Check whether a row already exists in the database with one or more
    key(column), value pairs from the provided data dictionary.
    :param schema: The schema instance that is calling the validator.
    :param data: the dictionary with data to validate.
    :param model: the model to validate against. It assumes the model has an
                  id column.
    '''
    unique_columns = [c.key for c in model.__table__.columns if c.unique]

    # this returns a list with sqlalchemy filter conditions. for example:
    # [User.username == 'joey', User.email == 'joey@gmail.com']
    # That list if filter conditions can then be passed to the query.filter
    # method.
    conditions = [getattr(model, column) == data.get(column)
                  for column in unique_columns
                  if data.get(column)]

    # this is the id of the existing object, if it is passed.
    update_id = schema.context.get('update_id', None)

    if conditions:
        # We want to filter the conditions with the 'OR' SQL operator.
        or_clause = or_(*conditions)
        query = model.query.filter(or_clause)

        if update_id is not None:
            # we don't care about collisions with 'self'.
            query = query.filter(model.id != update_id)

        objects = query.all()

        errors = {column: '{} is already in use.'.format(column.title())
                  for column in unique_columns
                  for object_ in objects
                  if getattr(object_, column) == data.get(column)}

        if errors:
            raise ValidationError(errors, 'conflicts')


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


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta):
        _SchemaOpts.__init__(self, meta)
        self.strict = True


class Schema(_Schema):
    OPTIONS_CLASS = SchemaOpts

    def __init__(self, page=None, expand=None, *args, **kwargs):
        super(Schema, self).__init__(*args, **kwargs)
        self.expand = expand or []
        self.page = page

    @post_dump(pass_many=True)
    def wrap_in_pagination(self, data, many):
        if many and self.page:
            page = PaginationSchema().dump(self.page).data
            page.update(items=data)
            return page


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


class ActionSchema(Schema):
    FAVORITE = 'favorite'
    UNFAVORITE = 'unfavorite'

    id = HashIDField(required=True)
    action = fields.Str(
        required=True,
        validate=validate.OneOf([FAVORITE, UNFAVORITE],
                                error='Must be one of {choices}'))
