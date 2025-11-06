"""
FI: ORAOwl-sovelluksen asetukset (settings.py)
    Tämä tiedosto sisältää kaikki keskeiset Django-asetukset.
    Kaikki kommentit ovat kaksikielisiä (FI/EN) projektin sääntöjen mukaisesti.

EN: Django settings for the ORAOwl project.
    Includes all main configurations with bilingual comments (FI/EN).
"""

from pathlib import Path
import os
import environ

# ============================================================================
# Base directory / Peruspolku
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# Environment variables / Ympäristömuuttujien lataus
# ============================================================================
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# ============================================================================
# Security / Tietoturva
# ============================================================================
# FI: Salainen avain (.env-tiedostossa, ei koskaan julkisesti)
# EN: Secret key (stored in .env, never committed to repository)
SECRET_KEY = env("SECRET_KEY")

# FI: Kehityksessä DEBUG=True, tuotannossa False
# EN: DEBUG=True for development, False for production
DEBUG = env("DEBUG")

# FI: Sallitut isäntäosoitteet (kehityksessä voidaan asettaa oletus)
# EN: Allowed hosts list (can define a default for development)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ============================================================================
# Application definition / Sovelluksen määrittely
# ============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "oraw_app",
    "sass_processor",
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

ROOT_URLCONF = "oraowl.urls"

# ============================================================================
# Templates / Templatet
# ============================================================================
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

WSGI_APPLICATION = "oraowl.wsgi.application"

# ============================================================================
# Database / Tietokanta
# ============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ============================================================================
# Password validation / Salasanavalidointi
# ============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================================
# Internationalization / Kansainvälistäminen
# ============================================================================
# FI: Käytetään suomen kieltä ja Suomen aikavyöhykettä.
# EN: Use Finnish language and Finnish time zone.
LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"

USE_I18N = True
USE_TZ = True

# ============================================================================
# Static and media files / Staattiset ja mediatiedostot
# ============================================================================
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# FI: SCSS-käännös ja hakupolut
# EN: SCSS compilation and search paths
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]

SASS_PROCESSOR_ENABLED = True
SASS_PROCESSOR_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# ============================================================================
# Authentication and Email / Kirjautuminen ja sähköposti
# ============================================================================
LOGIN_URL = "oraw_app:login"             # FI: minne @login_required ohjaa
LOGIN_REDIRECT_URL = "oraw_app:home"     # FI: minne siirrytään kirjautumisen jälkeen

# FI: Kehityksessä sähköpostit tulostetaan konsoliin.
# EN: In development, emails are printed to console.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "ORAOwl <no-reply@oraowl.local>"

# ============================================================================
# GDPR & Privacy (for future extension) / GDPR ja tietosuoja (laajennettava)
# ============================================================================
# FI: Näitä asetuksia voidaan täydentää myöhemmin (esim. tietojen anonymisointi, auditointi).
# EN: Reserved for future GDPR-related settings (e.g., anonymization, audit logging).

# Example placeholders:
# PRIVACY_ALLOW_ANONYMIZATION = True
# PRIVACY_AUDIT_ENABLED = True

# ============================================================================
# Default primary key / Oletus-ID
# ============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
