"""Production settings: Supabase Postgres, Resend email, WhiteNoise, HTTPS.

Selected automatically by ``wsgi.py`` / ``asgi.py`` and can be requested
explicitly with ``DJANGO_SETTINGS_MODULE=crelume.settings.prod``.

Required environment variables (the app refuses to start without them):

- ``DJANGO_SECRET_KEY`` — at least 50 characters
- ``DJANGO_ALLOWED_HOSTS`` — comma-separated public hostnames
- ``SITE_URL`` — public HTTPS base URL
- ``DATABASE_URL`` — Supabase Postgres connection string
- ``RESEND_API_KEY`` — Resend API key
- ``RECAPTCHA_PUBLIC_KEY`` / ``RECAPTCHA_PRIVATE_KEY`` — real reCAPTCHA v2 keys
"""

import os

from django.core.exceptions import ImproperlyConfigured

import dj_database_url

from .base import *  # noqa: F401,F403
from .base import env_bool, env_list

DEBUG = False


def required(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(
            f"{name} must be set when DJANGO_SETTINGS_MODULE=crelume.settings.prod."
        )
    return value


SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be at least 50 characters long.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must list the public hostname(s), comma-separated."
    )

SITE_URL = required("SITE_URL").rstrip("/")
if not SITE_URL.startswith("https://"):
    raise ImproperlyConfigured("SITE_URL must be the public https:// URL.")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "") or [SITE_URL]

# ---------- Database: Supabase Postgres ----------
DATABASE_URL = required("DATABASE_URL")
if not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise ImproperlyConfigured(
        "DATABASE_URL must be a Postgres connection string "
        "(use Supabase's pooler connection string)."
    )

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
        conn_health_checks=True,
        # Supabase's transaction pooler (port 6543) does not support
        # server-side cursors.
        disable_server_side_cursors=env_bool("DB_DISABLE_SERVER_SIDE_CURSORS", True),
        ssl_require=env_bool("DATABASE_SSL_REQUIRE", True),
    )
}

# ---------- Email: Resend via django-anymail ----------
ANYMAIL = {
    "RESEND_API_KEY": required("RESEND_API_KEY"),
}
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"

# ---------- reCAPTCHA ----------
RECAPTCHA_PUBLIC_KEY = required("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = required("RECAPTCHA_PRIVATE_KEY")
TEST_KEYS = {
    "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI",  # Google's public test keys
    "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe",
}
if RECAPTCHA_PUBLIC_KEY in TEST_KEYS or RECAPTCHA_PRIVATE_KEY in TEST_KEYS:
    raise ImproperlyConfigured(
        "Replace Google's reCAPTCHA test keys with real v2 keys before deploying."
    )

SILENCED_SYSTEM_CHECKS = []

# ---------- Static files: WhiteNoise ----------
# WhiteNoise sits directly after SecurityMiddleware so static responses still get
# HTTPS redirects and security headers.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_MAX_AGE = int(os.getenv("WHITENOISE_MAX_AGE", "31536000"))

# ---------- HTTPS / proxy ----------
if env_bool("DJANGO_BEHIND_PROXY", True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
# Platform health checks hit the app over plain HTTP internally.
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", True
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
