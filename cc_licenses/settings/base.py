"""
Django settings for cc_licenses project.
"""
# Standard library
import os

# Third-party
from babel import Locale
from django.conf.locale import LANG_INFO

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# SETTINGS_DIR is where this settings file is
SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_DIR is the directory under root that contains the settings directory,
#             urls.py, and other global stuff.
PROJECT_DIR = os.path.dirname(SETTINGS_DIR)
# ROOT_DIR is the top directory under source control
ROOT_DIR = os.path.dirname(PROJECT_DIR)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "licenses",
    "i18n",
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

ROOT_URLCONF = "cc_licenses.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dealer.contrib.django.context_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "cc_licenses.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "cc_licenses",
    }
}

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(ROOT_DIR, "public", "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = "/media/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}
    },
    "formatters": {
        "basic": {
            "format": "%(asctime)s %(name)-20s %(levelname)-8s %(message)s",
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "basic",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
    },
    "root": {
        "handlers": [
            "console",
        ],
        "level": "INFO",
    },
}

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en"  # "en" matches our default language code in Transifex

# https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# Teach Django about a few more languages
mi = Locale.parse("mi")
LANG_INFO["mi"] = {  # Maori
    "bidi": False,
    "code": "mi",
    "name": mi.get_display_name("en"),  # in english
    "name_local": mi.get_display_name("mi"),  # in their own language
}
LANG_INFO["ms"] = {  # Malay
    "bidi": False,
    "code": "ms",
    "name": "Malay",
    "name_local": "Bahasa Melayu",  # ??
}
LANG_INFO["zh-Hans"] = {
    "fallback": ["zh-hans"],
}
LANG_INFO["zh-Hant"] = {
    "fallback": ["zh-hant"],
}
LANG_INFO["oci"] = {  # Occitan? https://iso639-3.sil.org/code/oci
    "bidi": False,
    "code": "oci",
    "name": "Occitan",
    "name_local": "Occitan",
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "America/New_York"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(ROOT_DIR, "public", "static")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (os.path.join(PROJECT_DIR, "static"),)

# If using Celery, tell it to obey our logging configuration.
CELERYD_HIJACK_ROOT_LOGGER = False

# https://docs.djangoproject.com/en/1.9/topics/auth/passwords/#password-validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation.MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation.CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth."
            "password_validation.NumericPasswordValidator"
        ),
    },
]

# Make things more secure by default. Run "python manage.py check --deploy"
# for even more suggestions that you might want to add to the settings,
# depending on how the site uses SSL.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"

# template_fragments
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
    "branchstatuscache": {
        # Use memory caching so template fragments get cached whether we have
        # memcached running or not.
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}
# This will use memcached if we have it, and otherwise just not cache.
if "CACHE_HOST" in os.environ:
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.memcached.MemcachedCache",
        "LOCATION": "%(CACHE_HOST)s" % os.environ,
    }

# Percent translated that languages should be at or above
TRANSLATION_THRESHOLD = 80

# Location of the translation data's repo. Look in env for
# TRANSLATION_REPOSITORY_DIRECTORY.
# Default is next to this one.
TRANSLATION_REPOSITORY_DIRECTORY = os.getenv(
    "TRANSLATION_REPOSITORY_DIRECTORY",
    os.path.join(ROOT_DIR, "..", "cc-licenses-data"),
)

# django-distill settings
DISTILL_DIR = f"{TRANSLATION_REPOSITORY_DIRECTORY}/build/"

# Django translations are in the translation repo directory, under "locale".
# License translations are in the translation repo directory, under
# "translations".
LOCALE_PATHS = (
    os.path.join(TRANSLATION_REPOSITORY_DIRECTORY, "locale"),
    os.path.join(TRANSLATION_REPOSITORY_DIRECTORY, "legalcode"),
)

TRANSIFEX = {
    "ORGANIZATION_SLUG": "creativecommons",
    "PROJECT_SLUG": "CC",
    "API_TOKEN": os.getenv("TRANSIFEX_API_TOKEN", "missing"),
}

# The git branch where the official, approved, used in production translations
# are.
OFFICIAL_GIT_BRANCH = "main"

# Path to private keyfile to use when pushing up to data repo
TRANSLATION_REPOSITORY_DEPLOY_KEY = os.getenv(
    "TRANSLATION_REPOSITORY_DEPLOY_KEY", ""
)
