import os
from datetime import timedelta
from pathlib import Path
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-sfxtedi$dh=#e!n=#nwmi35^(26o0(z556j5-7d+^%e#n3t6$z'
DEBUG = True
ALLOWED_HOSTS = ["mardex.digitallaboratory.uz", "127.0.0.1", "localhost"]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    "https://mardex.digitallaboratory.uz"
]


INSTALLED_APPS = [
    'daphne',
    'django.contrib.gis',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # kutubxonalar
    "channels",
    'modeltranslation',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_yasg',
    'corsheaders',

    'client.apps.ClientConfig',
    'worker.apps.WorkerConfig',
    'job.apps.JobConfig',
    'users.apps.UsersConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]



# WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }


DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'mardex',
        'USER': 'user_mardex',
        'PASSWORD': 'password_mardex',
        'HOST': 'mardex_db',
        'PORT': '5432',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'mardex',  # PostgreSQL bazasi nomi
#         'USER': 'user_mardex',  # PostgreSQL foydalanuvchi nomi
#         'PASSWORD': 'password_mardex',  # PostgreSQL paroli
#         'HOST': 'mardex_db',  # Docker Compose'dagi konteyner nomi
#         'PORT': '5432',  # PostgreSQL uchun standart port
#     }
# }




# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/.

LANGUAGE_CODE = 'uz'

LANGUAGES = (
    ('ru', _('Russian')),
    ('uz', _('Uzbek')),
    ('en', _('English')),
)

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static'), ]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# settings.py
AUTH_USER_MODEL = 'users.AbstractUser'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=365 * 100),  # 100 yil amal qiladi
    'REFRESH_TOKEN_LIFETIME': timedelta(days=365 * 100),  # Refresh token ham 100 yil amal qiladi
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB (baytlarda)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",  # ️ yoki "redis://127.0.0.1:6379/1" — agar localda
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],  # Redis server ishlayotgan manzil va port
        },
    },
}

# workerlarni topishda km ni sozlash
NEAREST_WORKER_MIN_RADIUS_KM = 1
NEAREST_WORKER_MAX_RADIUS_KM = 30
NEAREST_WORKER_MAX_RESULTS = 20

load_dotenv()

MYID_BASE_URL = os.environ.get("MYID_BASE_URL")
MYID_CLIENT_ID = os.environ.get("MYID_CLIENT_ID")
MYID_CLIENT_SECRET = os.environ.get("MYID_CLIENT_SECRET")
MYID_CLIENT_HASH_ID = os.getenv("MYID_CLIENT_HASH_ID")
MYID_CLIENT_HASH = os.getenv("MYID_CLIENT_HASH")

ATMOS_BASE_URL = os.environ.get("ATMOS_BASE_URL")
ATMOS_CONSUMER_KEY = os.environ.get("ATMOS_CONSUMER_KEY")
ATMOS_CONSUMER_SECRET = os.environ.get("ATMOS_CONSUMER_SECRET")
ATMOS_STORE_ID = os.environ.get("ATMOS_STORE_ID")


CRYPTO_KEY = "N2s9EF9lZ97yCvMnxlsm2tTQz6GADqSftlQe7T5zOAM="
