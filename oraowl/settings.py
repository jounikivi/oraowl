"""
FI: ORAOwl-sovelluksen asetukset (settings.py)
    Tämä tiedosto sisältää kaikki keskeiset Django-asetukset.
    Kommentit ovat suomeksi ja englanniksi projektin sääntöjen mukaisesti.

EN: Django settings for the ORAOwl project.
    Includes all main configurations with Finnish/English comments.
"""

from pathlib import Path
#import os
import environ

# FI: Voiko käyttäjä rekisteröityä itse?
# EN: Is self-service user registration allowed?
# devissä True, livessä voidaan asettaa False
REGISTRATION_OPEN = False 

# ============================================================================
# Base directory / Peruspolku
# ============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# Environment configuration / Ympäristömuuttujat
# ============================================================================
# FI: Käytetään django-environ -kirjastoa lukemaan .env-tiedoston arvot.
# EN: Use django-environ to read environment variables from .env file.
env = environ.Env(
    DEBUG=(bool, True),
)

# FI: Luetaan .env-tiedosto projektin juuressa (jos se on olemassa).
# EN: Read .env file from project root (if it exists).
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

# ============================================================================
# Security / Turvallisuus
# ============================================================================
# FI: Tuotannossa SECRET_KEY tulee aina .env-tiedostosta tai Renderin env-muuttujista.
# EN: In production, SECRET_KEY must come from .env or Render environment variables.
SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-me")

# FI: DEBUG luetaan ympäristöstä. Paikallisesti True, Renderissä False.
# EN: DEBUG comes from environment. True for local dev, False on Render.
DEBUG = env.bool("DEBUG", default=True)

# FI: Render-ympäristössä ALLOWED_HOSTS asetetaan env-muuttujalla, esim.:
#     ALLOWED_HOSTS=oraowl.onrender.com
# EN: On Render, set ALLOWED_HOSTS via env, e.g.:
#     ALLOWED_HOSTS=oraowl.onrender.com
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost"]
)

# ============================================================================
# Application definition / Sovelluksen määrittely
# ============================================================================
INSTALLED_APPS = [
    # Django core apps / Djangon ydin-sovellukset
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps / Kolmannen osapuolen sovellukset
    "sass_processor",  # jos käytätte SASSia

    # Local apps / Paikalliset sovellukset
    "oraw_app",
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # FI: Whitenoise voidaan lisätä myöhemmin, jos halutaan palvella staticeja suoraan.
    # EN: Whitenoise can be added later if you want to serve static files via app server.
    # "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "oraowl.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # FI: Voit lisätä erillisen templates-kansion tänne, jos tarvitset.
            # EN: You can add extra template dirs here if needed.
            # BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "oraowl.wsgi.application"

# ============================================================================
# Database / Tietokanta (SQLite demoa varten)
# ============================================================================
# FI: Demoversiossa käytetään SQLiteä. Myöhemmin voidaan vaihtaa PostgreSQL:ään.
# EN: Use SQLite for the demo. You can switch to PostgreSQL later.
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
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ============================================================================
# Internationalization / Kieli- ja aikavyöhykeasetukset
# ============================================================================
LANGUAGE_CODE = "fi"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ============================================================================
# Static files (CSS, JS, images) / Staattiset tiedostot
# ============================================================================
# FI: STATIC_ROOT = polku, johon collectstatic kerää tiedostot.
# EN: STATIC_ROOT = where collectstatic will collect static files.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# FI: STATICFILES_DIRS = omat staattiset tiedostot (esim. /static).
# EN: STATICFILES_DIRS = your own static directories (e.g. /static).
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# FI: SASS-processori: mistä SASS-tiedostot löytyvät.
# EN: SASS processor settings.
SASS_PROCESSOR_ENABLED = True
SASS_PROCESSOR_ROOT = BASE_DIR / "static"

# Jos myöhemmin otetaan Whitenoise käyttöön:
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ============================================================================
# Authentication redirects / Kirjautumisen uudelleenohjaukset
# ============================================================================
# FI: Voit säätää nämä projektin URL-nimien mukaisiksi.
# EN: Adjust these to match your URL names.
LOGIN_URL = "oraw_app:login"
LOGIN_REDIRECT_URL = "oraw_app:home"
LOGOUT_REDIRECT_URL = "oraw_app:home"

# ============================================================================
# Default primary key / Oletus-ID-tyyppi
# ============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
