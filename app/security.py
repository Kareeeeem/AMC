import bcrypt
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, \
    SignatureExpired, BadSignature
from werkzeug.security import safe_str_cmp


def hash_password(password, rounds=13):
    if isinstance(password, unicode):
        password = str(password.encode('u8'))

    return bcrypt.hashpw(password, bcrypt.gensalt(rounds))


def verify_password(password, password_hash):
    '''Hash the given password and verify it with self.password_hash
    :param str password: the given password.
    '''
    if isinstance(password, unicode):
        password = password.encode('u8')

    if isinstance(password_hash, unicode):
        password_hash = password_hash.encode('u8')

        return safe_str_cmp(bcrypt.hashpw(password, password_hash),
                            password_hash)


def generate_auth_token(id, secret_key, expiration=3600, **kwargs):
    s = Serializer(secret_key, expires_in=expiration)
    payload = {'id': id}
    if kwargs:
        payload.update(kwargs)
    return s.dumps(payload)


def verify_auth_token(session, secret_key, token):
    s = Serializer(secret_key)
    try:
        return s.loads(token)
    except (SignatureExpired, BadSignature):
        return None
