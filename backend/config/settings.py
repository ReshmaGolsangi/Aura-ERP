"""Settings. Override via environment variables for production."""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env(path):
    """Read KEY=VALUE lines from backend/.env (written by the CONFIGURE .bat files)."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').replace("\\n", "\n"))


_load_env(BASE_DIR / ".env")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")   # SET THIS IN PRODUCTION
DEBUG = os.getenv("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "erp",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages"]},
}]
WSGI_APPLICATION = "config.wsgi.application"

# SQLite by default. For PostgreSQL set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST.
if os.getenv("DB_NAME"):
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql", "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"), "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"), "PORT": os.getenv("DB_PORT", "5432")}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "erp.User"
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(hours=12)}

# Business settings
COMPANY_PREFIX = os.getenv("COMPANY_PREFIX", "AUR")   # numbers look like AUR/QT/2026-27/0001
DEFAULT_GST = 18

# ---- Company details printed on every PDF (override with env vars) ----
COMPANY_NAME = os.getenv("COMPANY_NAME", "Aura Software")
COMPANY_ADDRESS = os.getenv("COMPANY_ADDRESS", "Your address line 1\nCity, State - PIN")
COMPANY_GSTIN = os.getenv("COMPANY_GSTIN", "27XXXXXXXXXXXXX")
COMPANY_STATE = os.getenv("COMPANY_STATE", "Maharashtra")   # decides CGST+SGST vs IGST
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "sales@example.com")
COMPANY_PHONE = os.getenv("COMPANY_PHONE", "+91 00000 00000")
COMPANY_BANK = os.getenv("COMPANY_BANK", "Bank: XXXX|A/c Name: Aura Software|A/c No: 0000|IFSC: XXXX0000")  # '|' = new line

# ---- Email (set EMAIL_HOST etc. for real sending; otherwise emails print in the terminal) ----
if os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST"); EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", ""); EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_SSL = EMAIL_PORT == 465   # port 465 = SSL, 587 = STARTTLS
    EMAIL_USE_TLS = not EMAIL_USE_SSL
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", COMPANY_EMAIL)

# ---- WhatsApp Cloud API (Meta). Leave blank => app gives a click-to-chat link instead ----
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
COMPANY_LOGO = os.getenv("COMPANY_LOGO", "")   # optional: full path to a PNG/JPG logo shown on purchase orders
