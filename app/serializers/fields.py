from marshmallow import fields, ValidationError
from app import hashid


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
