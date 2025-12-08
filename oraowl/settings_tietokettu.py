"""
===========================================================
 ORAOwl – Tietokettu/Production Settings (oraowl.fi)
 ORAOwl – Tietoketun tuotantoasetukset (oraowl.fi)
-----------------------------------------------------------
 This settings module extends the default development
 settings and overrides only values required for a secure
 and stable deployment on the Tietokettu platform.

 Tämä asetustiedosto laajentaa kehitysasetuksia ja korvaa
 vain ne asetukset, joita tarvitaan turvalliseen ja
 vakaaseen Tietokettu-julkaisuun.
===========================================================
"""

# Import all base settings from the main settings module.
# Tuo kaikki perusasetukset pääasetustiedostosta.
from .settings import *  # noqa: F403


# ---------------------------------------------------------
# General Django Settings / Yleiset Django-asetukset
# ---------------------------------------------------------

# Never enable DEBUG in production.
# Ei koskaan DEBUG=True tuotannossa.
DEBUG = False

# Allowed domain names for the deployed site.
# Sallitut domainit julkaistulle sivustolle.
ALLOWED_HOSTS = [
    "oraowl.fi",
    "www.oraowl.fi",
]


# ---------------------------------------------------------
# Security (CSRF / Trusted Origins)
# Turvallisuus (CSRF / Luotetut alkuperät)
# ---------------------------------------------------------

# Domains trusted for CSRF protection.
# CSRF-suojauksessa luotetut domainit.
CSRF_TRUSTED_ORIGINS = [
    "https://oraowl.fi",
    "https://www.oraowl.fi",
]

# Security options – enable once HTTPS has been confirmed working.
# Turva-asetukset – ota käyttöön, kun HTTPS toimii varmasti.
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True


# ---------------------------------------------------------
# Static Files / Staattiset tiedostot
# ---------------------------------------------------------

# Directory where collectstatic places compiled static files.
# Hakemisto, johon collectstatic kerää valmiit staattiset tiedostot.
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405


# ---------------------------------------------------------
# Registration / Käyttäjien rekisteröinti
# ---------------------------------------------------------

# Close public registration during demo/testing.
# Sulkee julkisen rekisteröitymisen demo/testausvaiheessa.
REGISTRATION_OPEN = False


# ---------------------------------------------------------
# Logging (Optional) / Lokitus (valinnainen)
# ---------------------------------------------------------
# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#     },
#     "root": {
#         "handlers": ["console"],
#         "level": "INFO",
#     },
# }


"""
End of Tietokettu production settings.
Tietoketun tuotantoasetusten loppu.
"""
# ============================================================================