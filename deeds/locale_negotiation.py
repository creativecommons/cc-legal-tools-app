# Locale negotiation tools
import os


CACHED_APPLICABLE_LANGS = {}
MO_PATH = "FIXME SET MO_PATH OR DO NOT USE"


def negotiate_locale(locale, mo_path=MO_PATH):
    """
    Choose the appropriate locale, using fallbacks, given the
    'requested' locale.

    Actually just a wrapper function for applicable_langs().
    """
    return applicable_langs(locale, mo_path)[0]


def applicable_langs(locale, mo_path=MO_PATH):
    """
    Return all available languages "applicable" to a requested locale.
    """
    cache_key = (locale, mo_path)
    if cache_key in CACHED_APPLICABLE_LANGS:
        return CACHED_APPLICABLE_LANGS[cache_key]

    applicable_langs = []
    if os.path.exists(os.path.join(mo_path, locale)):
        applicable_langs.append(locale)

    if '_' in locale:
        root_lang = locale.split('_')[0]
        if os.path.exists(os.path.join(mo_path, root_lang)):
            applicable_langs.append(root_lang)

    if not 'en' in applicable_langs:
        applicable_langs.append('en')

    # Don't cache silly languages that only fallback to en anyway, to
    # (semi-)prevent caching infinite amounts of BS
    if not locale == 'en' and len(applicable_langs) == 1:
        return applicable_langs

    CACHED_APPLICABLE_LANGS[cache_key] = applicable_langs
    return applicable_langs
