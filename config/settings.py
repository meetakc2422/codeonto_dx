"""Django settings for the Codeonto dashboard. Values come from .env (see .env.example)."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def db_from_url(url: str) -> dict:
    u = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": u.path.lstrip("/"),
        "USER": u.username or "",
        "PASSWORD": u.password or "",
        "HOST": u.hostname or "localhost",
        "PORT": str(u.port or 5432),
    }


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [h for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in env("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

if not DEBUG:
    # behind nginx, which terminates TLS and sets X-Forwarded-Proto
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.masters",
    "apps.outlets",
    "apps.reviews",
    "apps.stockouts",
    "apps.complaints",
    "apps.insights",
    "apps.uptime",
    "apps.payouts",
    "apps.billing",
    "apps.listings",
    "apps.alerts",
    "apps.integrations",
    "apps.assistant",
    "apps.metrics",
    "apps.competition",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": db_from_url(env("DATABASE_URL", "postgresql://localhost:5432/codeonto_app")),
}
# Read-only pipeline database used by the catalog sync / import commands
PIPELINE_DATABASE_URL = env("PIPELINE_DATABASE_URL", "postgresql://localhost:5432/dashboard_v1")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIR = BASE_DIR / "frontend"

REST_FRAMEWORK = {
    # Same login as Django admin (session cookie); every API call needs a logged-in user,
    # and apps.outlets.access limits what each user sees.
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.outlets.authentication.SessionAuth"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # stay logged in for two weeks
CSRF_COOKIE_HTTPONLY = False  # the dashboard reads it to send X-CSRFToken

# Platform integrations
ZOMATO_BASE_URL = env("ZOMATO_BASE_URL", "https://api.zomato.com/merchant-gw/web")
ZOMATO_COOKIE_FILE = env("ZOMATO_COOKIE_FILE")
SWIGGY_SESSION_FILE = env("SWIGGY_SESSION_FILE")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")

# Password reset links: where they point (empty = the address the request came in on), and how long they last
DASHBOARD_URL = env("DASHBOARD_URL")
PASSWORD_RESET_TIMEOUT = 60 * 60

# Outgoing mail (alerts, password resets). Without EMAIL_HOST the mails are printed to the console instead of sent.
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = int(env("EMAIL_PORT", "465"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_USE_TLS = EMAIL_PORT == 587
# the sender address; with Amazon SES EMAIL_HOST_USER is an access key, not an address, so set EMAIL_FROM
DEFAULT_FROM_EMAIL = env("EMAIL_FROM") or env("DEFAULT_FROM_EMAIL") or (EMAIL_HOST_USER if "@" in (EMAIL_HOST_USER or "") else "") or "alerts@localhost"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"

# "Connect with Google" (clients link their Business Profile from the dashboard)
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET")
GOOGLE_OAUTH_REDIRECT_URI = env("GOOGLE_OAUTH_REDIRECT_URI")
GOOGLE_TOKEN_KEY = env("GOOGLE_TOKEN_KEY")
COLLECTOR_DIR = env("COLLECTOR_DIR", str(BASE_DIR / "collector"))

# AI assistant (read-only): its own database role, a signing secret for per-client scope, and the model
ASSISTANT_DATABASE_URL = env("ASSISTANT_DATABASE_URL")
ASSISTANT_SCOPE_SECRET = env("ASSISTANT_SCOPE_SECRET")
ASSISTANT_MODEL = env("ASSISTANT_MODEL", "claude-sonnet-5-5")
ASSISTANT_MAX_ROWS = int(env("ASSISTANT_MAX_ROWS", "200"))
ASSISTANT_STATEMENT_TIMEOUT_MS = int(env("ASSISTANT_STATEMENT_TIMEOUT_MS", "8000"))
ASSISTANT_MAX_STEPS = int(env("ASSISTANT_MAX_STEPS", "8"))
ASSISTANT_MESSAGES_PER_HOUR = int(env("ASSISTANT_MESSAGES_PER_HOUR", "40"))

# Google Places API (New): competitor lookup. A plain API key, separate from the Business Profile OAuth client
GOOGLE_API_KEY = env("GOOGLE_API_KEY", "")
# Maps JavaScript API key for the competition map. It is sent to browsers, so restrict it to this site's domains
GOOGLE_MAPS_BROWSER_KEY = env("GOOGLE_MAPS_BROWSER_KEY", "")
# Zomato customer-app session (headers) for competitor lookup; refresh with `manage.py zomato_app_session`
ZOMATO_APP_SESSION_FILE = env("ZOMATO_APP_SESSION_FILE", str(BASE_DIR / "sessions" / "zomato_app.json"))
# Swiggy customer-app session (headers) for competitor lookup; refresh with `manage.py swiggy_app_session`
# optional: base URL of the Windows menu proxy (windows_zomato_proxy.py), e.g. http://1.2.3.4:5000. Zomato's edge blocks
# datacenter IPs on /gw/menu, so production fetches menus through it; empty = call Zomato directly
ZOMATO_MENU_PROXY_URL = env("ZOMATO_MENU_PROXY_URL", "")
# shared secret sent as X-Proxy-Secret; must match MENU_PROXY_SECRET in the collector .env on that machine
ZOMATO_MENU_PROXY_SECRET = env("ZOMATO_MENU_PROXY_SECRET", "")
SWIGGY_APP_SESSION_FILE = env("SWIGGY_APP_SESSION_FILE", str(BASE_DIR / "sessions" / "swiggy_app.json"))

# WhatsApp alerts (Meta Cloud API) sent by `manage.py send_alerts`; templates are the ones approved for the business account
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_BEARER_TOKEN = env("WHATSAPP_BEARER_TOKEN", "")
WHATSAPP_TEMPLATE_LANG = env("WHATSAPP_TEMPLATE_LANG", "en")
ALERT_OFFLINE_MIN_MINUTES = int(env("ALERT_OFFLINE_MIN_MINUTES", "10"))  # offline this long before alerting (no flapping)
ALERT_LOOKBACK_HOURS = int(env("ALERT_LOOKBACK_HOURS", "6"))
ALERT_AD_SPIKE_X = float(env("ALERT_AD_SPIKE_X", "2"))
ALERT_AD_SPIKE_MIN = float(env("ALERT_AD_SPIKE_MIN", "500"))
