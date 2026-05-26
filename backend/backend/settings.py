from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-eyb1#49vn#8jwh^z=z&l-w%3#u%*jgg=5w74vufc8j^2e_&%#(')

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,web').split(',') if h.strip()
]

# Внутренний URL для POST активации из activate_user (Docker-сеть: http://web:8000/...).
DJANGO_INTERNAL_ACTIVATION_URL = os.getenv(
    'DJANGO_INTERNAL_ACTIVATION_URL',
    'http://web:8000/auth/users/activation/',
)

# Схема публичных ссылок в письмах (https в продакшене за reverse-proxy).
DJANGO_PUBLIC_URL_SCHEME = os.getenv('DJANGO_PUBLIC_URL_SCHEME', 'http').strip().lower()
if '://' in DJANGO_PUBLIC_URL_SCHEME:
    DJANGO_PUBLIC_URL_SCHEME = DJANGO_PUBLIC_URL_SCHEME.split('://', 1)[0]

_use_https_cookies = os.getenv('DJANGO_SECURE_COOKIES', '').strip().lower() in ('1', 'true', 'yes')
if _use_https_cookies:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
else:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False

USE_X_FORWARDED_HOST = True
# За nginx с proxy_set_header X-Forwarded-Proto https запрос считается безопасным.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

_hsts = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '0') or '0')
SECURE_HSTS_SECONDS = _hsts if _hsts > 0 else 0
if SECURE_HSTS_SECONDS:
    SECURE_HSTS_INCLUDE_SUBDOMAINS = (
        os.getenv('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False') == 'True'
    )
    SECURE_HSTS_PRELOAD = os.getenv('DJANGO_SECURE_HSTS_PRELOAD', 'False') == 'True'

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

INSTALLED_APPS = [
    'accounts.apps.AccountsConfig',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'djoser',
    'drf_yasg',

    'products.apps.ProductsConfig',
    'training.apps.TrainingConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'diplom'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
    }
}

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

AUTH_USER_MODEL = 'accounts.CustomUser'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'EXCEPTION_HANDLER': 'backend.exceptions.custom_exception_handler',
}

DJOSER = {
    'LOGIN_FIELD': 'username',
    'USER_CREATE_PASSWORD_RETYPE': False,
    'SERIALIZERS': {
        'user_create': 'accounts.serializers.CustomUserCreateSerializer',
        'user': 'accounts.serializers.CustomUserSerializer', 
        'current_user': 'accounts.serializers.CustomUserSerializer', 
    },

    'SEND_ACTIVATION_EMAIL': True,
    'ACTIVATION_URL': 'activate/{uid}/{token}',
    'SEND_CONFIRMATION_EMAIL': False,

    'ACTIVATION_EXPIRED_DAYS': 3,
    'USERNAME_RESET_CONFIRM_URL': None,

    'PERMISSIONS': {
        'user_list': ['rest_framework.permissions.IsAdminUser'],
        'user': ['djoser.permissions.CurrentUserOrAdmin'],
    },
    'EMAIL': {
        'activation': 'accounts.email.ActivationEmail'
    },
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Введите ваш JWT токен в формате: Bearer <ваш_токен>'
        }
    },
    'USE_SESSION_AUTH': False,
    'LANG': 'ru',
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg.inspectors.SwaggerAutoSchema',
    'DEFAULT_API_URL': os.getenv('SWAGGER_BASE_URL', 'http://127.0.0.1:2224'),
    'DEEP_LINKING': True,
}

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        'DJANGO_CSRF_TRUSTED_ORIGINS',
        'http://127.0.0.1,http://localhost:2224',
    ).split(',')
    if o.strip()
]

CSRF_COOKIE_DOMAIN = None

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER', 'noreply@yourdomain.com')
SERVER_EMAIL = os.getenv('EMAIL_HOST_USER', 'noreply@yourdomain.com')

SITE_NAME = os.getenv('SITE_NAME', 'RICE')

# Путь к APK внутри контейнера/на сервере (см. .env.example и том releases в docker-compose).
MOBILE_APK_PATH = os.getenv('MOBILE_APK_PATH', '')

# Ссылка в письме при смене почты: по умолчанию — GET на этот же бэкенд.
# Для диплинка в приложение задайте шаблон, например: riceapp://email-change?token={token}
EMAIL_CHANGE_CONFIRM_URL_TEMPLATE = os.getenv('EMAIL_CHANGE_CONFIRM_URL_TEMPLATE', '')
# Время жизни signed-token для смены почты (секунды, по умолчанию 3 суток).
EMAIL_CHANGE_CONFIRM_MAX_AGE_SECONDS = int(
    os.getenv('EMAIL_CHANGE_CONFIRM_MAX_AGE_SECONDS', str(3 * 24 * 60 * 60))
)
EMAIL_CHANGE_MAIL_SUBJECT = os.getenv(
    'EMAIL_CHANGE_MAIL_SUBJECT', 'Подтверждение новой почты'
)

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
