"""
============== Configurações Django ==============
"""

from pathlib import Path
import os

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- .env ----------
# pip install python-dotenv
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

# ---------- Ambiente ----------
ENV = os.getenv("DJANGO_ENV", "local").strip().lower()  # "local" (default) ou "prod"
IS_PROD = ENV == "prod"

# ---------- Segurança ----------
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-secret-key-change-me" if not IS_PROD else None
)
if IS_PROD and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY não definida em produção. Configure a env var SECRET_KEY.")

DEBUG = False if IS_PROD else True

# Domínio no PythonAnywhere
PA_DOMAIN = "navarro03.pythonanywhere.com"

ALLOWED_HOSTS = [
    PA_DOMAIN,
    "localhost",
    "127.0.0.1",
    "[::1]",
] if IS_PROD else ["*", "localhost", "127.0.0.1", "[::1]"]

CSRF_TRUSTED_ORIGINS = [
    f"https://{PA_DOMAIN}",
    "http://localhost",
    "http://127.0.0.1",
    "http://[::1]",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
] if IS_PROD else [
    "http://localhost",
    "http://127.0.0.1",
    "http://[::1]",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Cookies seguros apenas em produção/https
SESSION_COOKIE_SECURE = IS_PROD
CSRF_COOKIE_SECURE = IS_PROD

# Se estiver atrás de proxy/HTTPS gerenciado
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if IS_PROD else None

# ---------- Apps ----------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "game",
]

# ---------- Middleware ----------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------- URLs / WSGI ----------
ROOT_URLCONF = "snake_ladders.urls"
WSGI_APPLICATION = "snake_ladders.wsgi.application"

# ---------- Templates ----------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # pasta global de templates
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------- Banco de dados ----------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.expanduser("~/data/db.sqlite3"),
    }
}

# ---------- Senhas ----------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------- Localização ----------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ---------- Arquivos estáticos ----------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"         # onde collectstatic escreve
STATICFILES_DIRS = [BASE_DIR / "static"]       # seus assets locais

# ---------- STORAGES ----------
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
}

# ---------- Primary key default ----------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Logging básico ----------
LOG_LEVEL = "INFO" if IS_PROD else "DEBUG"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "game:tela_inicial"
LOGOUT_REDIRECT_URL = "game:tela_inicial"