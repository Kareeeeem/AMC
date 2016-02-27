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
                    token_type='bearer')

    @classmethod
    def verify_auth_token(cls, token):
        s = Serializer(cls.SECRET_KEY)
        try:
            return s.loads(token)
        except (SignatureExpired, BadSignature):
            return None
