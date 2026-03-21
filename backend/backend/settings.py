import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-local-dev-only-change-in-prod')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    'localhost,127.0.0.1,0.0.0.0'
).split(',')

# ── Apps ──────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'social_django',
    'neurohire',
]

# ── Middleware ────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves static files on Railway
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'backend.urls'

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
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# ── Database (SQLite for auth/sessions) ──────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── MongoDB (candidates) ──────────────────────────────────────────────────
MONGODB_URI = os.environ.get(
    'MONGODB_URI',
    'mongodb+srv://ammuhhharshi_db_user:WWwGcTrD39wL0MYd@cluster0.kr8penf.mongodb.net/neurohire?retryWrites=true&w=majority&appName=Cluster0'
)
MONGODB_DB = os.environ.get('MONGODB_DB', 'neurohire')

# ── Auth ──────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY    = os.environ.get('GOOGLE_CLIENT_ID', '')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
SOCIAL_AUTH_URL_NAMESPACE        = 'social'
LOGIN_REDIRECT_URL               = '/'
LOGOUT_REDIRECT_URL              = '/'

# After Google OAuth success — redirect to frontend
SOCIAL_AUTH_LOGIN_REDIRECT_URL   = 'https://neurohire-bay.vercel.app/SeekerDashboard'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = 'https://neurohire-bay.vercel.app/SeekerDashboard'
SOCIAL_AUTH_LOGIN_ERROR_URL      = 'https://neurohire-bay.vercel.app/'

# Pipeline to set user role after social auth
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'neurohire.pipeline.save_user_profile',
    'neurohire.pipeline.set_redirect_url',
)

# Allow social auth to use next param for redirect
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = ['neurohire-bay.vercel.app']

# ── Internationalisation ──────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'UTC'
USE_I18N      = True
USE_TZ        = True

# ── Static files (WhiteNoise) ─────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── File uploads ──────────────────────────────────────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── CORS ──────────────────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS   = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://localhost:3000'
).split(',')
# Allow all in dev, restrict to listed origins in prod
CORS_ALLOW_ALL_ORIGINS = DEBUG
# Always allow these regardless of env
CORS_ORIGIN_WHITELIST  = [
    'https://neurohire-bay.vercel.app',
    'http://localhost:5173',
    'http://localhost:3000',
]

CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization',
    'content-type', 'dnt', 'origin',
    'user-agent', 'x-csrftoken', 'x-requested-with',
]
CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']

# ── Recruiter domain whitelist ────────────────────────────────────────────
ALLOWED_RECRUITER_DOMAINS = [
    'company.com', 'corp.com', 'enterprise.com',
    'hr.com', 'recruit.com', 'hiring.com',
]

# ── REST Framework ────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}