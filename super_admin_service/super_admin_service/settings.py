
# ============================================================================
from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv
import logging
import os


# logging.warning("🔥 SETTINGS LOADED — FILE PATH: " + os.path.abspath(__file__))

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "fallback-secret-key")
SECRET_KEY = "super-secret-shared-key"


DEBUG = True
ALLOWED_HOSTS = []
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'admin_core',
    'dynamic_services.apps.DynamicServicesConfig',
    'dynamic_pricing',
    'dynamic_facilities',
    'dynamic_categories',
    'plans_coupens',
    'pets',
    'corsheaders',
    'provider_home',
    'dynamic_fields',
    'dynamic_permissions',
]

AUTH_USER_MODEL = "admin_core.SuperAdmin"
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vue dev server
    "http://127.0.0.1:5174",
]
CORS_ALLOW_ALL_ORIGINS = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal"]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 👈 must be first or near-top
    'django.middleware.common.CommonMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'admin_core.middleware.sync_verified_user.SyncVerifiedUserMiddleware',
    'middleware.log_auth_header.LogAuthHeaderMiddleware',
]
# import logging
# logging.warning("🔥 ACTIVE MIDDLEWARE ORDER:")
# for m in MIDDLEWARE:
#     logging.warning(" - " + m)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'admin_core.authentication.CentralAuthJWTAuthentication',  # shared JWT
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    "SIGNING_KEY": SECRET_KEY,  # must match auth_service
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}
ROOT_URLCONF = 'super_admin_service.urls'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.environ.get('POSTGRES_DB', 'Super_Admin'),
#         'USER': os.environ.get('POSTGRES_USER', 'postgres'),
#         'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
#         'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        
#         'PORT': os.environ.get('POSTGRES_PORT', '5432'),
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'Super_Admin',
        'USER': 'petleo',
        'PASSWORD': 'petleo',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR.parent, 'service_provider_service', 'media')

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'  # Required for admin and staticfiles app
STATICFILES_DIRS = [BASE_DIR / "static"]  # Optional: for project-level static files
STATIC_ROOT = BASE_DIR / "staticfiles"    # Optional: for collectstatic in production

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],  # optional, you can create a templates folder
        'APP_DIRS': True,  # important: allows Django to find admin templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # required by admin
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

KAFKA_BROKER_URL = os.environ.get("KAFKA_BROKER_URL", "localhost:9093")
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
KAFKA_USER_TOPIC = "user_created"
KAFKA_GROUP_ID = "superadmin_group"
SERVICE_NAME = "super_admin_service"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'kafka': {
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
