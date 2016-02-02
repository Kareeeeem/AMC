import os
import logging
from logging import handlers

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    CSRF_ENABLED = True
    DEBUG = False
    TESTING = False
    LOGGING_LEVEL = 'DEBUG'
    BASEDIR = basedir

    @staticmethod
    def add_loghandler(logger, loglevel, logfile):
        logger.setLevel(getattr(logging, loglevel, 'DEBUG'))
        log_handler = handlers.RotatingFileHandler(logfile,
                                                   maxBytes=5*1024*1024,
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
    DEBUG = True
    SECRET_KEY = 'seekrit'
    DATABASE_URI = os.environ.get('DEV_DATABASE_URI')
    SQLALCHEMY_ECHO = False
    BCRYPT_ROUNDS = 4


class TestingConfig(DevelopmentConfig):
    TESTING = True
    SECRET_KEY = 'seekrit'
    BCRYPT_ROUNDS = 4
    DATABASE_URI = os.environ.get('TEST_DATABASE_URI')


class ProductionConfig(Config):
    LOGGING_LEVEL = 'WARNING'
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_URI = os.environ.get('PROD_DATABASE_URL')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
