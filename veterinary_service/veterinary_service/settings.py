
from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
import environ

env = environ.Env()
# environ.Env.read_env() # We rely on docker env vars or .env file

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "super-secret-shared-key"

DEBUG = True

ALLOWED_HOSTS = ["*"]

CORS_ALLOW_ALL_HEADERS = True
CORS_ALLOW_ALL_ORIGINS = True
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-reset-token",    
    "x-clinic-id",
]

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'django_celery_beat',
    'corsheaders',
    'channels',
    'veterinary',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'veterinary.middleware.VeterinaryPermissionMiddleware',
]

ROOT_URLCONF = 'veterinary_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'veterinary_service.wsgi.application'
ASGI_APPLICATION = 'veterinary_service.asgi.application'

# Redis Channel Layer for WebSockets
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(env('REDIS_HOST', default='127.0.0.1'), env.int('REDIS_PORT', default=6379))],
        },
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'veterinary_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
        'PORT': os.environ.get('POSTGRES_PORT', '5436'),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'veterinary.authentication.ShadowUserAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    "SIGNING_KEY": SECRET_KEY,
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "USER_ID_FIELD": "username",
    "USER_ID_CLAIM": "user_id",
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Kafka
KAFKA_BROKER_URL = os.environ.get('KAFKA_BROKER_URL', 'localhost:9093')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'veterinary': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Celery Configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

CELERY_BEAT_SCHEDULE = {
    'process-vaccination-deworming-reminders-every-5-minutes': {
        'task': 'veterinary.tasks.process_vaccination_deworming_reminders',
        'schedule': 300.0, # 5 minutes
    },
    'check-due-medicine-reminders-every-15-minutes': {
        'task': 'veterinary.tasks.check_due_medicine_reminders',
        'schedule': 900.0, # 15 minutes
    },
}
