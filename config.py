import fractions
import logging
import os
import random
from logging import handlers

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SQLALCHEMY_ECHO = False
    CSRF_ENABLED = True
    DEBUG = False
    TESTING = False
    LOGGING_LEVEL = 'DEBUG'
    BASEDIR = basedir
    BCRYPT_ROUNDS = 12
    # one month
    TOKEN_EXPIRATION = 3600 * 24 * 30

    OBSCURE_ID_MODULUS = 2 ** 20 - -1
    # has to be coprime to OBSCURE_ID_MODULUS
    OBSCURE_ID_KEY = 542174

    # find a coprime by running this function
    def find_coprime(self, modulus=None):
        modulus = modulus or self.OBSCURE_ID_MODULUS
        # every number has a coprime so this loop will always terminate.
        while True:
            other = random.randrange(modulus)
            if fractions.gcd(modulus, other) == 1:
                break
        return other

    @staticmethod
    def add_loghandler(logger, loglevel, logfile):
        logger.setLevel(getattr(logging, loglevel, 'DEBUG'))
        log_handler = handlers.RotatingFileHandler(logfile,
                                                   maxBytes=5 * 1024 * 1024,
                                                   backupCount=2)
        log_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        logger.addHandler(log_handler)

    @classmethod
    def init_loggers(cls, app=None):
        sqla_logger = logging.getLogger('sqlalchemy.engine')
        cls.add_loghandler(sqla_logger,
                           cls.LOGGING_LEVEL,
                           os.path.join(cls.BASEDIR, 'sqla.log'))
        if app:
            cls.add_loghandler(app.logger,
                               cls.LOGGING_LEVEL,
                               os.path.join(cls.BASEDIR, 'app.log'))


class DevelopmentConfig(Config):
    SQLALCHEMY_ECHO = True
    DEBUG = True
    SECRET_KEY = 'seekrit'
    HASHID_SALT = 'SaAaAalTy'
    BCRYPT_ROUNDS = 4
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URI')
    SERVER_NAME = 'localhost:5000'


class TestingConfig(DevelopmentConfig):
    SQLALCHEMY_ECHO = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URI')


class ProductionConfig(Config):
    LOGGING_LEVEL = 'WARNING'
    SECRET_KEY = os.environ.get('SECRET_KEY')
    OBSCURE_ID_KEY = os.environ.get('OBSCURE_ID_KEY')
    HASHID_SALT = os.environ.get('HASHID_SALT')
    SQLALCHEMY_DATABASE_URI = os.environ.get('PROD_DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
