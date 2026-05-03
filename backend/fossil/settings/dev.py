from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fossil',
        'USER': 'fossil',
        'PASSWORD': 'fossil',
        'HOST': 'db',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

CORS_ALLOW_ALL_ORIGINS = True
