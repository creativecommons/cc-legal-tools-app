"""
Every license can be identified by a URL, e.g. "http://creativecommons.org/licenses/by-nc-sa/4.0/"
or "http://creativecommons.org/licenses/by-nc-nd/2.0/tw/".  In the RDF, this is the rdf:about
attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation of the license
with the url in the dc:source's rdf:resource attribute.

Some licenses ahve a dcq:isReplacedBy element.

"""
import os

import polib
from django.conf import settings
from django.db import models
from django.utils import translation

from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import get_translation_object
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.templatetags.license_tags import build_deed_url, build_license_url
from licenses.transifex import TransifexHelper

MAX_LANGUAGE_CODE_LENGTH = 8


DJANGO_LANGUAGE_CODES = {
    # CC language code: django language code
    "zh-Hans": "zh_Hans",
    "zh-Hant": "zh_Hant",
}


class LegalCode(models.Model):
    license = models.ForeignKey(
        "licenses.License", on_delete=models.CASCADE, related_name="legal_codes"
    )
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?",
    )
    html_file = models.CharField(
        max_length=300, help_text="HTML file we got this from", blank=True, default=""
    )

    translation_last_update = models.DateTimeField(
        help_text="The last_updated field from Transifex for this translation",
        null=True,
        default=None,
    )

    class Meta:
        ordering = ["license__about"]

    def __str__(self):
        return f"LegalCode<{self.language_code}, {self.license.about}>"

    @property
    def django_language_code(self):
        """A few of the language codes as used to identify the license
        translations 'officially' are a little different from what Dango
        uses for the same case.
        """
        return DJANGO_LANGUAGE_CODES.get(self.language_code, self.language_code)

    def branch_name(self):
        """
        If this translation is modified, what is the name of the GitHub branch
        we'll use to manage the modifications?
        Basically its "{license code}-{version}-{language}[-{jurisdiction code}",
        except that all the "by* 4.0" licenses use "cc4" for the license_code part.
        This has to be a valid DNS domain, so we also change any _ to - and
        remove any periods.
        """
        license = self.license
        parts = []
        if license.license_code.startswith("by") and license.version == "4.0":
            parts.append("cc4")
        else:
            parts.extend([license.license_code, license.version])
        parts.append(self.language_code)
        if license.jurisdiction_code:
            parts.append(license.jurisdiction_code)
        return "-".join(parts).replace("_", "-").replace(".", "").lower()

    def license_url(self):
        """
        URL to view this translation of this license
        """
        license = self.license
        return build_license_url(
            license.license_code,
            license.version,
            license.jurisdiction_code,
            self.language_code,
        )

    def deed_url(self):
        """
        URL to view this translation of this deed
        """
        license = self.license
        return build_deed_url(
            license.license_code,
            license.version,
            license.jurisdiction_code,
            self.language_code,
        )

    def fat_code(self):
        """
        Returns e.g. 'CC BY-SA 4.0' - all upper case etc. No language.
        """
        return self.license.fat_code()

    @property
    def translation_domain(self):
        return self.license.resource_slug

    def get_translation_object(self):
        domain = self.license.resource_slug
        return get_translation_object(language_code=self.language_code, domain=domain)

    def get_pofile(self) -> polib.POFile:
        with open(self.translation_filename(), "rb") as f:
            content = f.read()
        return polib.pofile(content.decode(), encoding="utf-8")

    def get_english_pofile(self) -> polib.POFile:
        if self.language_code != DEFAULT_LANGUAGE_CODE:
            # Same license, just in English translation:
            english_legalcode = License.get_legalcode_for_language_code(
                DEFAULT_LANGUAGE_CODE
            )
            return english_legalcode.get_pofile()
        return self.get_pofile()

    def translation_filename(self):
        """
        Return absolute path to the .po file with this translation.
        These are in the cc-licenses-data repository, in subdirectories:
          - "legalcode/"
          - language code (should match what Django uses, not what Transifex uses)
          - "LC_MESSAGES/"  (Django insists on this)
          - files

        The filenames are {resource_slug}.po (get the resource_slug
        from the license).

        e.g. for the BY-NC 4.0 French translation, which has no jurisdiction,
        the filename will be "by-nc_4.0.po", and in full,
        "{translation repo topdir}/legalcode/fr/by-nc_4.0.po".
        """
        filename = f"{self.license.resource_slug}.po"
        fullpath = os.path.join(
            settings.TRANSLATION_REPOSITORY_DIRECTORY,
            "legalcode",
            self.django_language_code,
            "LC_MESSAGES",
            filename,
        )
        return fullpath


class License(models.Model):
    about = models.URLField(
        max_length=200,
        help_text="The license's unique identifier, e.g. 'http://creativecommons.org/licenses/by-nd/2.0/br/'",
        unique=True,
    )
    license_code = models.CharField(
        max_length=40,
        help_text="shorthand representation for which class of licenses this falls into.  "
        "E.g. 'by-nc-sa', or 'MIT', 'nc-sampling+', 'devnations', ...",
    )
    version = models.CharField(
        max_length=3, help_text="E.g. '4.0'. Not required.", blank=True, default=""
    )
    jurisdiction_code = models.CharField(max_length=9, blank=True, default="")
    creator_url = models.URLField(
        max_length=200,
        blank=True,
        default="",
        help_text="E.g. http://creativecommons.org",
    )
    license_class_url = models.URLField(
        max_length=200,
        help_text="E.g. http://creativecommons.org/license/",
        blank=True,
        default="",
    )

    source = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="source_of",
        help_text="another license that this is the translation of",
    )

    is_replaced_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replaces",
        help_text="another license that has replaced this one",
    )
    is_based_on = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="base_of",
        help_text="another license that this one is based on",
    )

    deprecated_on = models.DateField(
        null=True, help_text="if set, the date on which this license was deprecated"
    )

    permits_derivative_works = models.BooleanField()
    permits_reproduction = models.BooleanField()
    permits_distribution = models.BooleanField()
    permits_sharing = models.BooleanField()

    requires_share_alike = models.BooleanField()
    requires_notice = models.BooleanField()
    requires_attribution = models.BooleanField()
    requires_source_code = models.BooleanField()

    prohibits_commercial_use = models.BooleanField()
    prohibits_high_income_nation_use = models.BooleanField()

    class Meta:
        ordering = ["-version", "license_code", "jurisdiction_code"]

    def __str__(self):
        return f"License<{self.about}>"

    def get_legalcode_for_language_code(self, language_code):
        """
        Return the legalcode for this license and language.
        If language_code has a "-" and we don't find it, try
        without the "-*" part (to handle e.g. "en-us").
        """
        if not language_code:
            language_code = translation.get_language()
        try:
            return self.legal_codes.get(language_code=language_code)
        except LegalCode.DoesNotExist:
            if "-" in language_code:  # e.g. "en-us"
                lang = language_code.split("-")[0]
                return self.legal_codes.get(language_code=lang)
            raise

    @property
    def resource_name(self):
        """Human-readable name for the translation resource for this license"""
        return self.fat_code()

    @property
    def resource_slug(self):
        # Transifex translation resource slug for this license.
        # letters, numbers, underscores or hyphens.
        # No periods.
        if self.jurisdiction_code:
            slug = f"{self.license_code}_{self.version}_{self.jurisdiction_code}"
        else:
            slug = f"{self.license_code}_{self.version}"
        slug = slug.replace(".", "")
        return slug

    def rdf(self):
        """Generate RDF for this license?"""
        return "RDF Generation Not Implemented"  # FIXME if needed

    def fat_code(self):
        """
        Returns e.g. 'CC BY-SA 4.0' - all upper case etc. No language.
        """
        license = self
        s = f"{license.license_code} {license.version}"
        if license.license_code.startswith("by"):
            s = f"CC {s}"
        if license.jurisdiction_code:
            s = f"{s} {license.jurisdiction_code}"
        s = s.upper()
        return s

    @property
    def level_of_freedom(self):
        if self.license_code in ("devnations", "sampling"):
            return FREEDOM_LEVEL_MIN
        elif (
            self.license_code.find("sampling") > -1
            or self.license_code.find("nc") > -1
            or self.license_code.find("nd") > -1
        ):
            return FREEDOM_LEVEL_MID
        else:
            return FREEDOM_LEVEL_MAX

    @property
    def superseded(self):
        return self.is_replaced_by is not None

    @property
    def sampling_plus(self):
        return self.license_code in ("nc-sampling+", "sampling+")

    @property
    def include_share_adapted_material_clause(self):
        return self.license_code in ["by", "by-nc"]

    def tx_upload_messages(self):
        """
        Upload the messages to Transifex,
        creating the resource if it doesn't already exist.
        """
        # Have to do English first, they get uploaded differently as the "source" messages
        # and are required if we need to first create the resource in Transifex.
        en_legalcode = self.get_legalcode_for_language_code(DEFAULT_LANGUAGE_CODE)
        helper = TransifexHelper()
        helper.upload_messages_to_transifex(legalcode=en_legalcode)
        for legalcode in self.legal_codes.exclude(language_code=DEFAULT_LANGUAGE_CODE):
            helper.upload_messages_to_transifex(legalcode=legalcode)


class TranslationBranch(models.Model):
    branch_name = models.CharField(max_length=40)
    legalcodes = models.ManyToManyField("LegalCode")
    version = models.CharField(
        max_length=3, help_text="E.g. '4.0'. Not required.", blank=True, default=""
    )
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?",
    )
    last_transifex_update = models.DateTimeField(
        "Time when last updated on Transifex.", null=True, blank=True,
    )
    complete = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "translation branches"

    def __str__(self):
        return f"Translation branch {self.branch_name}. {'Complete' if self.complete else 'In progress'}."

    @property
    def stats(self):
        untranslated_messages = 0
        translated_messages = 0
        for code in self.legalcodes.all():
            pofile = code.get_pofile()
            untranslated_messages += len(pofile.untranslated_entries())
            translated_messages += len(pofile.translated_entries())
        total_messages = untranslated_messages + translated_messages
        if total_messages:
            percent = int(translated_messages * 100 / float(total_messages))
        else:
            percent = 100
        return {
            "untranslated_messages": untranslated_messages,
            "translated_messages": translated_messages,
            "total_messages": total_messages,
            "percent": percent,
        }
