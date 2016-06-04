from marshmallow import ValidationError
from sqlalchemy import or_


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
                  if data.get(column) and getattr(object_, column) == data.get(column)}

        if errors:
            raise ValidationError(errors, 'conflicts')
