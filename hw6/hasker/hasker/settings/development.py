"""
DEVELOPMENT settings
"""

from .base import *


DEBUG = True
SECRET_KEY = 'kh&qsk!!75bwf0-xkrcu499c8hptob(=27c(hfm0gl8&4l$fai'
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
INTERNAL_IPS = ("127.0.0.1", )
INSTALLED_APPS.append("debug_toolbar")
MIDDLEWARE.append("debug_toolbar.middleware.DebugToolbarMiddleware")

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': root('db.sqlite3'),
    }
}

MEDIA_ROOT = root('media')
STATIC_ROOT = root('static')
