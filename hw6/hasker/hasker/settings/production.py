"""
PRODUCTION settings
"""

from .base import *


DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = root("tmp", "emails")

MEDIA_ROOT = '/var/www/media/'
STATIC_ROOT = '/var/www/static/'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '',
    }
}
