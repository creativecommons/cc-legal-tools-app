"""
Every license can be identified by a URL, e.g.
"https://creativecommons.org/licenses/by-nc-sa/4.0/" or
"https://creativecommons.org/licenses/by-nc-nd/2.0/tw/". In the RDF, this is
the rdf:about attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation
of the license with the url in the dc:source's rdf:resource attribute.

Some licenses ahve a dcq:isReplacedBy element.
"""
# Standard library
import os
import posixpath

# Third-party
import polib
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import translation
from django.utils.translation import gettext

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import (
    active_translation,
    cc_to_django_language_code,
    cc_to_filename_language_code,
    get_default_language_for_jurisdiction,
    get_translation_object,
)
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.constants import EXCLUDED_LANGUAGE_IDENTIFIERS
from licenses.transifex import TransifexHelper

MAX_LANGUAGE_CODE_LENGTH = 8

UNITS_LICENSES = [
    "by",
    "by-nc",
    "by-nc-nd",  # in versions > 1.0
    "by-nc-sa",
    "by-nd",
    "by-nd-nc",  # in version 1.0 unported, 1.0 ported
    "by-sa",
    "nc",  # ..... in versions 2.0-jp, 1.0 unported, 1.0 ported
    "nc-sa",  # .. in versions 2.0-jp, 1.0 unported, 1.0 ported
    "nd",  # ..... in versions 2.0-jp, 1.0 unported, 1.0 ported
    "nd-nc",  # .. in versions 2.0-jp, 1.0 unported, 1.0 ported
    "sa",  # ..... in versions 2.0-jp, 1.0 unported, 1.0 ported
]
UNITS_PUBLIC_DOMAIN = [
    "CC0",
]


class LegalCodeQuerySet(models.QuerySet):
    # We'll create LegalCode and License objects for all the by licenses,
    # and the zero_1.0 ones.
    # We're just doing these license codes and versions for now:
    # by* 4.0
    # by* 3.0 - including ported
    # cc 1.0

    # Queries for legalcode objects
    LICENSES_ALL_QUERY = Q(
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_40_QUERY = Q(
        license__version="4.0",
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_30_QUERY = Q(
        license__version="3.0",
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_25_QUERY = Q(
        license__version="2.5",
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_21_QUERY = Q(
        license__version="2.1",
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_20_QUERY = Q(
        license__version="2.0",
        license__license_code__in=UNITS_LICENSES,
    )
    LICENSES_10_QUERY = Q(
        license__version="1.0",
        license__license_code__in=UNITS_LICENSES,
    )

    # There's only one version of CC0.
    PUBLIC_DOMAIN_ALL_QUERY = Q(license__license_code__in=UNITS_PUBLIC_DOMAIN)

    def translated(self):
        """
        Return a queryset of the LegalCode objects that we are doing the
        translation process on.
        """
        # We are not translating the 3.0 unported licenses - they are English
        # only We are not translating the 3.0 ported licenses - just storing
        # their HTML as-is.
        return self.exclude(license__version="3.0")

    def valid(self):
        """
        Return a queryset of the LegalCode objects that exist and are valid
        ones that we expect to work. This will change over time as we add
        support for more licenses.
        """

        return self.filter(
            self.LICENSES_ALL_QUERY | self.PUBLIC_DOMAIN_ALL_QUERY
        ).exclude(language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS)

    def validgroups(self):
        """
        Return a queryset of the LegalCode objects that exist and are valid
        ones that we expect to work. This will change over time as we add
        support for more licenses.
        """

        return {
            "Licenses 4.0": self.filter(self.LICENSES_40_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Licenses 3.0": self.filter(self.LICENSES_30_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Licenses 2.5": self.filter(self.LICENSES_25_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Licenses 2.1": self.filter(self.LICENSES_21_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Licenses 2.0": self.filter(self.LICENSES_20_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Licenses 1.0": self.filter(self.LICENSES_10_QUERY).exclude(
                language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS
            ),
            "Public Domain all": self.filter(
                self.PUBLIC_DOMAIN_ALL_QUERY
            ).exclude(language_code__in=EXCLUDED_LANGUAGE_IDENTIFIERS),
        }


class LegalCode(models.Model):
    license = models.ForeignKey(
        "licenses.License",
        on_delete=models.CASCADE,
        related_name="legal_codes",
    )
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?"
        " This is the language code used by CC, which might be a little"
        " different from the Django language code.",
    )
    html_file = models.CharField(
        max_length=300,
        help_text="HTML file we got this from",
        blank=True,
        default="",
    )
    translation_last_update = models.DateTimeField(
        help_text="The last_updated field from Transifex for this translation",
        null=True,
        default=None,
    )
    title = models.CharField(
        max_length=112,
        help_text="License title in this language, e.g."
        " 'Attribution-NonCommercial-NoDerivs 3.0 Unported'",
        blank=True,
        default="",
    )
    html = models.TextField(blank=True, default="")
    license_url = models.URLField(null=True, default=None)
    deed_url = models.URLField(unique=True)
    plain_text_url = models.URLField(null=True, default=None)

    objects = LegalCodeQuerySet.as_manager()

    class Meta:
        ordering = ["license", "language_code"]

    def __str__(self):
        return f"LegalCode<{self.language_code}, {self.license}>"

    def save(self, *args, **kwargs):
        unit = self.license.license_code
        self.deed_url = build_path(
            self.license.about,
            "deed",
            self.language_code,
        )
        self.license_url = build_path(
            self.license.about,
            "legalcode",
            self.language_code,
        )
        if (
            (unit in UNITS_LICENSES and float(self.license.version) > 2.5)
            or unit == "CC0"
        ) and self.language_code == "en":
            self.plain_text_url = build_path(
                self.license.about,
                "legalcode.txt",
                self.language_code,
            )
        super().save(*args, **kwargs)

    def _get_save_path(self):
        """
        If saving the deed or license as a static file, this returns
        the relative path where the saved file should be, not including
        the actual filename.

        For unported, uses "xu" as the "jurisdiction" in the filename.

        If saving the license as a static file, this returns the relative
        path of the file to save it as.

        4.0 formula:
        /licenses/VERSION/LICENSE_deed_LANGAUGE.html
        /licenses/VERSION/LICENSE_legalcode_LANGAUGEhtml

        4.0 examples:
        /licenses/4.0/by-nc-nd_deed_en.html
        /licenses/4.0/by-nc-nd_legalcode_en.html
        /licenses/4.0/by_deed_en.html
        /licenses/4.0/by_legalcode_en.html
        /licenses/4.0/by_deed_zh-Hans.html
        /licenses/4.0/by_legalcode_zh-Hans.html

        3.0 formula:
        /licenses/VERSION/JURISDICTION/LICENSE_deed_LANGAUGE.html
        /licenses/VERSION/JURISDICTION/LICENSE_legalcode_LANGAUGE.html

        3.0 examples:
        /licenses/3.0/xu/by_deed_en.html
        /licenses/3.0/xu/by_legalcode.en.html
        /licenses/3.0/am/by_deed_hy.html
        /licenses/3.0/am/by_legalcode_hy.html
        /licenses/3.0/rs/by_deed_rs-Cyrl.html
        /licenses/3.0/rs/by_legalcode_rs-Cyrl.html
        For jurisdiction, I used "xu" to mean "unported".
        See https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2#User-assigned_code_elements.  # noqa: E501

        cc0 formula:
        /publicdomain/VERSION/LICENSE_deed_LANGAUGE.html
        /publicdomain/VERSION/LICENSE_legalcode_LANGAUGE.html

        cc0 examples:
        /publicdomain/1.0/zero_deed_en.html
        /publicdomain/1.0/zero_legalcode_en.html
        /publicdomain/1.0/zero_deed_ja.html
        /publicdomain/1.0/zero_legalcode_ja.html
        """

        license = self.license
        unit = (
            "zero"
            if license.license_code == "CC0"
            else license.license_code.lower()
        )
        if license.category == "licenses" and float(license.version) < 4.0:
            return os.path.join(
                license.category,  # licenses
                unit,  # by, by-nc-nd, etc.
                license.version,  # 1.0, 2.0, etc.
                license.jurisdiction_code or "xu",  # "xu" for "unported"
            )
        else:
            return os.path.join(
                license.category,  # licenses, publicdomain
                unit,  # by, by-nc-nd, zero, etc.
                license.version,  # 1.0, 4.0, etc.
            )

    def get_file_and_links(self, document):
        license = self.license
        unit = license.license_code
        juris_code = license.jurisdiction_code
        language_default = get_default_language_for_jurisdiction(juris_code)
        filename = os.path.join(
            self._get_save_path(),
            f"{document}.{self.language_code}.html",
        )
        symlinks = []
        if self.language_code == language_default:
            # Symlink default languages
            symlinks.append(f"{document}.html")
            if document == "deed":
                symlinks.append("index.html")
        if unit in UNITS_LICENSES and float(license.version) < 4.0:
            # Symlink Unported ("xu" jurisdiction)
            if not license.jurisdiction_code:
                symlinks.append(f"../{filename}")
                symlinks.append(f"../{document}.html")
                if document == "deed":
                    symlinks.append("../index.html")

        return [filename, symlinks]

    def has_english(self):
        """
        Return True if there's an English translation for the same license.
        """
        return (
            self.language_code == "en"
            or self.license.legal_codes.filter(language_code="en").exists()
        )

    def branch_name(self):
        """
        If this translation is modified, what is the name of the GitHub branch
        we'll use to manage the modifications?  Basically its "{license
        code}-{version}-{language}[-{jurisdiction code}", except that all the
        "by* 4.0" licenses use "cc4" for the license_code part. This has to be
        a valid DNS domain, so we also change any _ to - and remove any
        periods.
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
        return get_translation_object(
            django_language_code=cc_to_django_language_code(
                self.language_code
            ),
            domain=domain,
        )

    def get_pofile(self) -> polib.POFile:
        with open(self.translation_filename(), "rb") as f:
            content = f.read()
        return polib.pofile(content.decode(), encoding="utf-8")

    def get_english_pofile(self) -> polib.POFile:
        if self.language_code != DEFAULT_LANGUAGE_CODE:
            # Same license, just in English translation:
            english_legalcode = self.license.get_legalcode_for_language_code(
                DEFAULT_LANGUAGE_CODE
            )
            return english_legalcode.get_pofile()
        return self.get_pofile()

    def translation_filename(self):
        """
        Return absolute path to the .po file with this translation.
        These are in the cc-licenses-data repository, in subdirectories:
          - "legalcode/"
          - language code (should match what Django uses, not what Transifex
            uses)
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
            settings.DATA_REPOSITORY_DIR,
            "legalcode",
            cc_to_filename_language_code(self.language_code),
            "LC_MESSAGES",
            filename,
        )
        return fullpath


class License(models.Model):
    about = models.URLField(
        max_length=200,
        help_text="The license's unique identifier, e.g."
        " 'https://creativecommons.org/licenses/by-nd/2.0/br/'",
        unique=True,
    )
    license_code = models.CharField(
        max_length=40,
        help_text="shorthand representation for which class of licenses this"
        " falls into. E.g. 'by-nc-sa', or 'MIT', 'nc-sampling+',"
        " 'devnations', ...",
    )
    version = models.CharField(
        max_length=3,
        help_text="E.g. '4.0'. Not required.",
        blank=True,
        default="",
    )
    jurisdiction_code = models.CharField(max_length=9, blank=True, default="")
    creator_url = models.URLField(
        max_length=200,
        blank=True,
        default="",
        help_text="E.g. https://creativecommons.org",
    )
    category = models.CharField(
        max_length=13,
        help_text="'licenses' or 'publicdomain'",
        blank=True,
        default="",
    )
    title_english = models.TextField(
        help_text="License title in English, e.g."
        " 'Attribution-NonCommercial-NoDerivs 3.0 Unported'",
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
        null=True,
        help_text="if set, the date on which this license was deprecated",
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
        return (
            f"License<{self.license_code},{self.version},"
            f"{self.jurisdiction_code}>"
        )

    def get_metadata(self):
        """
        Return a dictionary with the metadata for this license.
        """
        data = {
            "license_code": self.license_code,
            "version": self.version,
            "title_english": self.title_english,
        }
        if self.jurisdiction_code:
            data["jurisdiction"] = self.jurisdiction_code

        data["permits_derivative_works"] = self.permits_derivative_works
        data["permits_reproduction"] = self.permits_reproduction
        data["permits_distribution"] = self.permits_distribution
        data["permits_sharing"] = self.permits_sharing
        data["requires_share_alike"] = self.requires_share_alike
        data["requires_notice"] = self.requires_notice
        data["requires_attribution"] = self.requires_attribution
        data["requires_source_code"] = self.requires_source_code
        data["prohibits_commercial_use"] = self.prohibits_commercial_use
        data[
            "prohibits_high_income_nation_use"
        ] = self.prohibits_high_income_nation_use

        data["translations"] = {}
        for lc in self.legal_codes.order_by("language_code"):
            language_code = lc.language_code
            with active_translation(lc.get_translation_object()):
                data["translations"][language_code] = {
                    "license": lc.license_url,
                    "deed": lc.deed_url,
                    "title": gettext(self.title_english),
                }

        return data

    def logos(self):
        """
        Return an iterable of the codes for the logos that should be
        displayed with this license. E.g.:
        ["cc-logo", "cc-zero", "cc-by"]
        """
        result = ["cc-logo"]  # Everybody gets this
        if self.license_code == "CC0":
            result.append("cc-zero")
        elif self.license_code.startswith("by"):
            result.append("cc-by")
            if self.prohibits_commercial_use:
                result.append("cc-nc")
            if self.requires_share_alike:
                result.append("cc-sa")
            if not self.permits_derivative_works:
                result.append("cc-nd")
        return result

    def get_legalcode_for_language_code(self, language_code):
        """
        Return the LegalCode object for this license and language.
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
        # All lowercase.
        if self.jurisdiction_code:
            slug = (
                f"{self.license_code}_{self.version}_{self.jurisdiction_code}"
            )
        else:
            slug = f"{self.license_code}_{self.version}"
        slug = slug.replace(".", "")
        return slug.lower()

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
        # Have to do English first, they get uploaded differently as the
        # "source" messages and are required if we need to first create the
        # resource in Transifex.
        en_legalcode = self.get_legalcode_for_language_code(
            DEFAULT_LANGUAGE_CODE
        )
        helper = TransifexHelper()
        helper.upload_messages_to_transifex(legalcode=en_legalcode)
        for legalcode in self.legal_codes.exclude(
            language_code=DEFAULT_LANGUAGE_CODE
        ):
            helper.upload_messages_to_transifex(legalcode=legalcode)

    @property
    def nc(self):
        return "nc" in self.license_code

    @property
    def nd(self):
        return "nd" in self.license_code

    @property
    def sa(self):
        return "sa" in self.license_code


class TranslationBranch(models.Model):
    branch_name = models.CharField(max_length=40)
    legalcodes = models.ManyToManyField("LegalCode")
    version = models.CharField(
        max_length=3,
        help_text="E.g. '4.0'. Not required.",
        blank=True,
        default="",
    )
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?"
        " This is a CC language code, which might differ from Django.",
    )
    last_transifex_update = models.DateTimeField(
        "Time when last updated on Transifex.",
        null=True,
        blank=True,
    )
    complete = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "translation branches"

    def __str__(self):
        return (
            f"Translation branch {self.branch_name}."
            f" {'Complete' if self.complete else 'In progress'}."
        )

    @property
    def stats(self):
        number_of_untranslated_messages = 0
        number_of_translated_messages = 0
        for code in self.legalcodes.all():
            pofile = code.get_pofile()
            number_of_untranslated_messages += len(
                pofile.untranslated_entries()
            )
            number_of_translated_messages += len(pofile.translated_entries())
        number_of_total_messages = (
            number_of_untranslated_messages + number_of_translated_messages
        )
        if number_of_total_messages:
            percent_messages_translated = int(
                number_of_translated_messages
                * 100
                / float(number_of_total_messages)
            )
        else:
            percent_messages_translated = 100
        return {
            "number_of_untranslated_messages": number_of_untranslated_messages,
            "number_of_translated_messages": number_of_translated_messages,
            "number_of_total_messages": number_of_total_messages,
            "percent_messages_translated": percent_messages_translated,
        }


def build_path(about, document, language_code):
    path = about.replace("https://creativecommons.org", "")
    if document == "legalcode.txt" or not language_code:
        path = posixpath.join(path, document)
    else:
        path = posixpath.join(path, f"{document}.{language_code}")
    return path
