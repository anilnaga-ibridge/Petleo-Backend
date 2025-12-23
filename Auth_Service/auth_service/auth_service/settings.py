




# ==========================================================================




from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
from decouple import config
import environ

env = environ.Env()
environ.Env.read_env()

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
USE_TZ = True
TIME_ZONE = "Asia/Kolkata"


SECRET_KEY = "super-secret-shared-key"


DEBUG = True
ALLOWED_HOSTS = []
CORS_ALLOW_ALL_HEADERS = True
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-reset-token",    
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'users',  # your custom user app
 
]
CORS_ALLOW_CREDENTIALS = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal"]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware',
    'middleware.update_last_activity.UpdateLastActivityMiddleware',

]
PIN_REVERIFY_TIMEOUT_MINUTES = 5  # Like GooglePay (set your preferred timeout)

ROOT_URLCONF = 'auth_service.urls'
# STATIC_URL = '/static/'  # Required
# STATICFILES_DIRS = [BASE_DIR / "static"]  
# STATIC_ROOT = BASE_DIR / "staticfiles"    


import os
from pathlib import Path

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / "static"
]

STATIC_ROOT = BASE_DIR / "staticfiles"


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

WSGI_APPLICATION = 'auth_service.wsgi.application'


AUTH_USER_MODEL = 'users.User'
# REST_FRAMEWORK = {
#     'DEFAULT_AUTHENTICATION_CLASSES': [
#         'rest_framework_simplejwt.authentication.JWTAuthentication',
#     ],
#     'DEFAULT_PERMISSION_CLASSES': [
#         'rest_framework.permissions.IsAuthenticated',
#     ],
# }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'Auth_Service',
        'USER': 'petleo',
        'PASSWORD': 'petleo',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}

# SIMPLE_JWT = {
#     "SIGNING_KEY": SECRET_KEY,  # must match in all services
#     "ALGORITHM": "HS256",
#     "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
#     "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
#     "USER_ID_FIELD": "id",
#     "USER_ID_CLAIM": "user_id",
#     "AUTH_HEADER_TYPES": ("Bearer",),
#     "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
# }

SIMPLE_JWT = {
    "SIGNING_KEY": SECRET_KEY,
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    # VERY IMPORTANT
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = "anil.naga@ibridge.digital"
EMAIL_HOST_PASSWORD = "jofh nauc ldot amas"   # Gmail App Password
# jofh nauc ldot amas
DEFAULT_FROM_EMAIL = "anil.naga@ibridge.digital"
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Email service settings
EMAIL_TIMEOUT = 30  # seconds
EMAIL_USE_LOCALTIME = False

# Logging configuration for email debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'users.email_utils': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'kafka': {
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
    },
}


# SMS
SMS_BACKEND = 'console'  


# OTP and rate limit settings
OTP_TTL_SECONDS = 60
OTP_RATE_LIMIT_WINDOW_SECONDS = 3600
OTP_RATE_LIMIT_MAX_PER_WINDOW = 5

# Refresh token life
REFRESH_TTL_DAYS = 14

# Kafka
KAFKA_BOOTSTRAP_SERVERS = [os.environ.get('KAFKA_BROKER_URL', 'localhost:9093')]

# Static superadmin (dev only)
STATIC_SUPERADMIN_PHONE = '9999999999'
STATIC_SUPERADMIN_OTP = '123456'


SERVICE_NAME = "auth_service"

KAFKA_BROKER = os.environ.get('KAFKA_BROKER_URL', 'localhost:9093')

KAFKA_EVENT_TOPIC = "service_events"



CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8080",
]
# ============================
# Redis Configuration (Correct)
# ============================
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_URL = "redis://127.0.0.1:6379/0"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Prevents downtime if Redis disconnects
        }
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
