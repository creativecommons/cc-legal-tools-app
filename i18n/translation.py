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


@functools.lru_cache(maxsize=500)
def get_translation_object(pofilepath, language_code):
    return Translation(pofilepath, language_code)
