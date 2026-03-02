import logging
import os
from importlib.util import find_spec
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_dotenv(filepath: Path):
    if not filepath.exists():
        return
    for raw_line in filepath.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def env(key: str, default=""):
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False):
    return str(os.getenv(key, str(default))).lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int = 0):
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: str = ""):
    value = env(key, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def has_module(module_name: str) -> bool:
    return find_spec(module_name) is not None


load_dotenv(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", "change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "apps.core",
    "apps.accounts",
    "apps.products",
    "apps.cart",
    "apps.orders",
    "apps.payments",
    "apps.dealership",
    "apps.blog",
]

SOCIAL_AUTH_ENABLED = env_bool("SOCIAL_AUTH_ENABLED", True)
ALLAUTH_AVAILABLE = all(
    has_module(module_name)
    for module_name in (
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
    )
)
SOCIAL_AUTH_AVAILABLE = SOCIAL_AUTH_ENABLED and ALLAUTH_AVAILABLE

SOCIAL_GOOGLE_CLIENT_ID = env("SOCIAL_GOOGLE_CLIENT_ID", "").strip()
SOCIAL_GOOGLE_SECRET = env("SOCIAL_GOOGLE_SECRET", "").strip()
SOCIAL_FACEBOOK_CLIENT_ID = env("SOCIAL_FACEBOOK_CLIENT_ID", "").strip()
SOCIAL_FACEBOOK_SECRET = env("SOCIAL_FACEBOOK_SECRET", "").strip()

SOCIAL_GOOGLE_ENABLED = SOCIAL_AUTH_AVAILABLE and bool(SOCIAL_GOOGLE_CLIENT_ID and SOCIAL_GOOGLE_SECRET)
SOCIAL_FACEBOOK_ENABLED = SOCIAL_AUTH_AVAILABLE and bool(SOCIAL_FACEBOOK_CLIENT_ID and SOCIAL_FACEBOOK_SECRET)

if SOCIAL_AUTH_AVAILABLE:
    INSTALLED_APPS += [
        "django.contrib.sites",
        "allauth",
        "allauth.account",
        "allauth.socialaccount",
    ]
    if SOCIAL_GOOGLE_ENABLED:
        INSTALLED_APPS.append("allauth.socialaccount.providers.google")
    if SOCIAL_FACEBOOK_ENABLED:
        INSTALLED_APPS.append("allauth.socialaccount.providers.facebook")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if SOCIAL_AUTH_AVAILABLE:
    try:
        auth_middleware_index = MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        MIDDLEWARE.insert(auth_middleware_index + 1, "allauth.account.middleware.AccountMiddleware")
    except ValueError:
        pass

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.global_settings",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DB_ENGINE = env("DB_ENGINE", "sqlite").lower()
if DB_ENGINE == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "oalt_ev"),
            "USER": env("DB_USER", "postgres"),
            "PASSWORD": env("DB_PASSWORD", "postgres"),
            "HOST": env("DB_HOST", "127.0.0.1"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 120),
            "CONN_HEALTH_CHECKS": env_bool("DB_CONN_HEALTH_CHECKS", True),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if env_bool("ATOMIC_REQUESTS", False):
    DATABASES["default"]["ATOMIC_REQUESTS"] = True

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MAX_AGE = env_int("WHITENOISE_MAX_AGE", 31536000 if not DEBUG else 0)
WHITENOISE_KEEP_ONLY_HASHED_FILES = env_bool("WHITENOISE_KEEP_ONLY_HASHED_FILES", not DEBUG)
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_ALLOW_ALL_ORIGINS = True
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = (
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "avif",
    "mp4",
    "webm",
    "woff",
    "woff2",
)
WHITENOISE_IMMUTABLE_FILE_TEST = r"^.+\.[0-9a-f]{8,12}\..+$"

ASSET_MINIFY_ENABLED = env_bool("ASSET_MINIFY_ENABLED", not DEBUG)
ASSET_VERSION = env("ASSET_VERSION", "")
CRITICAL_CSS_FILE = env("CRITICAL_CSS_FILE", "css/critical.min.css")
TAILWIND_CDN_ENABLED = env_bool("TAILWIND_CDN_ENABLED", True)
FONT_AWESOME_CDN_ENABLED = env_bool("FONT_AWESOME_CDN_ENABLED", True)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "core:home"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

if SOCIAL_AUTH_AVAILABLE:
    AUTHENTICATION_BACKENDS.append("allauth.account.auth_backends.AuthenticationBackend")
    SITE_ID = env_int("SITE_ID", 1)
    SOCIALACCOUNT_LOGIN_ON_GET = True
    SOCIALACCOUNT_STORE_TOKENS = True
    SOCIALACCOUNT_PROVIDERS = {}
    if SOCIAL_GOOGLE_ENABLED:
        SOCIALACCOUNT_PROVIDERS["google"] = {
            "SCOPE": ["profile", "email"],
            "AUTH_PARAMS": {"access_type": "online"},
            "APP": {
                "client_id": SOCIAL_GOOGLE_CLIENT_ID,
                "secret": SOCIAL_GOOGLE_SECRET,
                "key": "",
            },
        }
    if SOCIAL_FACEBOOK_ENABLED:
        SOCIALACCOUNT_PROVIDERS["facebook"] = {
            "METHOD": "oauth2",
            "SCOPE": ["email", "public_profile"],
            "FIELDS": ["id", "email", "name", "first_name", "last_name"],
            "APP": {
                "client_id": SOCIAL_FACEBOOK_CLIENT_ID,
                "secret": SOCIAL_FACEBOOK_SECRET,
                "key": "",
            },
        }

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "noreply@example.com")
SERVER_EMAIL = env("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
ADMINS = [tuple(item.split(":", 1)) for item in env_list("ADMINS", "") if ":" in item]

SITE_BASE_URL = env("SITE_BASE_URL", "http://127.0.0.1:8000")
WHATSAPP_PHONE = env("WHATSAPP_PHONE", "917291880088")
SALES_TEAM_EMAILS = env_list("SALES_TEAM_EMAILS", "")
SALES_TEAM_WHATSAPP_NUMBERS = env_list("SALES_TEAM_WHATSAPP_NUMBERS", "")
WHATSAPP_API_URL = env("WHATSAPP_API_URL", "")
WHATSAPP_API_TOKEN = env("WHATSAPP_API_TOKEN", "")

RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_CURRENCY = env("RAZORPAY_CURRENCY", "INR")

REDIS_URL = env("REDIS_URL", "").strip()
REDIS_BACKEND_AVAILABLE = has_module("django_redis")
if REDIS_URL and REDIS_BACKEND_AVAILABLE:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "oalt",
            "TIMEOUT": env_int("CACHE_TIMEOUT", 900),
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "oalt-ev-local-cache",
            "TIMEOUT": env_int("CACHE_TIMEOUT", 300),
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

CACHE_TTL = env_int("CACHE_TTL", 900)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", "strict-origin-when-cross-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = env("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = env("SECURE_CROSS_ORIGIN_RESOURCE_POLICY", "same-origin")

LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()
SQL_LOG = env_bool("SQL_LOG", False)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(name)s %(process)d %(thread)d %(message)s"},
        "simple": {"format": "%(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose" if not DEBUG else "simple",
            "level": LOG_LEVEL,
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG" if SQL_LOG else "INFO",
            "propagate": False,
        },
    },
}
logging.captureWarnings(True)

USE_CLOUDINARY = env_bool("USE_CLOUDINARY", False)
if has_module("cloudinary_storage"):
    cloudinary_cloud_name = env("CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key = env("CLOUDINARY_API_KEY")
    cloudinary_api_secret = env("CLOUDINARY_API_SECRET")
    cloudinary_enabled = USE_CLOUDINARY and all((cloudinary_cloud_name, cloudinary_api_key, cloudinary_api_secret))
    if cloudinary_enabled:
        CLOUDINARY_STORAGE = {
            "CLOUD_NAME": cloudinary_cloud_name,
            "API_KEY": cloudinary_api_key,
            "API_SECRET": cloudinary_api_secret,
        }
        DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
