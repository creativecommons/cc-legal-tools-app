"""
A Translation is an object representing a set of messages and
their translations. It corresponds quite closely to the data
stored in a .po file, with some methods added to make
efficient translation easier.
"""
import functools
import os
from builtins import FileNotFoundError

import polib
from django.conf import settings
from django.utils.safestring import mark_safe

from licenses.constants import VARYING_MESSAGE_IDS


class Translation:
    def __init__(self, pofilepath, language_code):
        self.language_code = language_code
        self.pofilepath = pofilepath
        if not os.path.exists(pofilepath):
            raise FileNotFoundError(pofilepath)
        self.pofile = polib.pofile(pofilepath)
        self.translations = {
            entry.msgid: mark_safe(entry.msgstr) for entry in self.pofile
        }

        # For debugging, you can dump the translations:
        # with open("translations.json", "w") as f:
        #     json.dump(self.translations, f, indent=2)

    def translate(self, msgid):
        if settings.DEBUG:
            default = f"[MISSING TRANSLATION FOR msgid='{msgid}' in pofile='{self.pofilepath}']"
        else:
            default = msgid
        return self.translations.get(msgid, default)

    # The rest of this is just for analyzing translation statistics, not needed to produce the site.
    def num_messages(self):
        return len(list(self.translations.keys()))

    def num_translated(self):
        return len(
            list(key for key in self.translations.keys() if self.translations[key])
        )

    def percent_translated(self):
        total = self.num_messages()
        if total > 0:
            return 100 * (self.num_translated() / total)
        return 0

    def compare_to(self, translation):
        """
        See how the given translation compares to this one.
        Returns a dictionary, hopefully keys are self-explanatory.
        """
        t1 = self
        t2 = translation
        self_keys = list(t1.translations.keys())
        given_keys = list(t2.translations.keys())

        keys_missing = set(self_keys) - set(given_keys)
        keys_extra = set(given_keys) - set(self_keys)
        keys_common = set(self_keys) & set(given_keys)
        different_translations = {}
        for key in keys_common:
            if key not in VARYING_MESSAGE_IDS:
                if t1.translations[key] != t2.translations[key]:
                    different_translations[key] = (
                        t1.translations[key],
                        t2.translations[key],
                    )
        return dict(
            keys_missing=keys_missing,
            keys_extra=keys_extra,
            keys_common=keys_common,
            different_translations=different_translations,
        )


@functools.lru_cache(maxsize=500)
def get_translation_object(pofilepath, language_code):
    return Translation(pofilepath, language_code)
