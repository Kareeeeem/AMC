import datetime

from itsdangerous import (
    BadSignature,
    SignatureExpired,
    TimedJSONWebSignatureSerializer as Serializer,
)
from sqlalchemy import DateTime, Column

from app.lib import with_app_config


class CreatedUpdatedMixin(object):
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)


@with_app_config('SECRET_KEY', 'TOKEN_EXPIRATION')
class TokenMixin(object):
    SECRET_KEY = ''
    TOKEN_EXPIRATION = 3600

    def generate_auth_token(self, expiration=None, **payload):
        expiration = expiration or self.TOKEN_EXPIRATION
        payload.update(dict(id=self.id))
        s = Serializer(self.SECRET_KEY, expires_in=expiration)

        return dict(access_token=s.dumps(payload),
                    expires_in=expiration,
                    token_type='Bearer')

    @classmethod
    def verify_auth_token(cls, token):
        s = Serializer(cls.SECRET_KEY)
        try:
            return s.loads(token)
        except (SignatureExpired, BadSignature):
            return None


class CRUDMixin(object):
    '''A mixin that provides some helper and proxy functions for easy object
    creation and updating with validation.
    '''
    @classmethod
    def create(cls, session, data, commit=True):
        '''Create an instance from a dictionary
        :param bool commit: a boolean stating wether to commit at the end.
        '''
        instance = cls(**data)
        return instance.save(session, commit=commit)

    def update(self, session, data, commit=True):
        '''Update an instance from a dictionary
        :param bool commit: a boolean stating wether to commit at the end
        '''
        for k, v in data.iteritems():
            setattr(self, k, v)
        return commit and self.save(session, commit=commit) or self

    def save(self, session, commit=True):
        '''Save an instance to the database.
        :param bool commit: a boolean stating wether to commit at the end.
        '''
        session.add(self)
        if commit:
            session.commit()
        return self

    def delete(self, session, commit=True):
        '''Delete an instance from the database.
        :param bool commit: a boolean stating wether to commit at the end.
        '''
        session.delete(self)
        return commit and session.commit()
