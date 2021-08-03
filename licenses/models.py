"""
Every license can be identified by a URL, e.g.
"https://creativecommons.org/licenses/by-nc-sa/4.0/" or
"https://creativecommons.org/licenses/by-nc-nd/2.0/tw/". In the RDF, this is
the rdf:about attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation
of the license with the url in the dc:source's rdf:resource attribute.

Some licenses have a dcq:isReplacedBy element.
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

# First-party/Local
from i18n import DEFAULT_LANGUAGE_CODE
from i18n.utils import (
    get_default_language_for_jurisdiction,
    get_jurisdiction_name,
    get_translation_object,
)
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN
from licenses.constants import EXCLUDED_LANGUAGE_IDENTIFIERS

# TODO: update as part of translation rewrite
# from licenses.transifex import TransifexHelper

MAX_LANGUAGE_CODE_LENGTH = 15

UNITS_LICENSES = [
    # Units are in all versions, unless otherwise noted:
    "by",
    "by-nc",
    "by-nc-nd",  # ........ in versions: > 1.0
    "by-nc-sa",
    "by-nd",
    "by-nd-nc",  # ........ in versions: 1.0 unported, 1.0 ported
    "by-sa",
    "devnations",  # ...... in versions: 2.0
    "nc",  # .............. in versions: 2.0-jp, 1.0 unported, 1.0 ported
    "nc-sa",  # ........... in versions: 2.0-jp, 1.0 unported, 1.0 ported
    "nc-sampling+",  # .... in versions: 1.0 unported, 1.0 ported
    "nd",  # .............. in versions: 2.0-jp, 1.0 unported, 1.0 ported
    "nd-nc",  # ........... in versions: 2.0-jp, 1.0 unported, 1.0 ported
    "sa",  # .............. in versions: 2.0-jp, 1.0 unported, 1.0 ported
    "sampling",  # ........ in versions: 1.0 unported, 1.0 ported
    "sampling+",  # ....... in versions: 1.0 unported, 1.0 ported
]
UNITS_PUBLIC_DOMAIN = [
    "mark",
    "publicdomain",
    "zero",
]
UNITS_DEPRECATED = {
    # Sorted by date, ascending:
    "nc": "2004-05-25",
    "nc-sa": "2004-05-25",
    "nc-sampling": "2004-05-25",
    "nd": "2004-05-25",
    "nd-nc": "2004-05-25",
    "sa": "2004-05-25",
    "devnations": "2007-06-04",
    "sampling": "2007-06-04",
    "publicdomain": "2010-10-11",
    "nc-sampling+": "2011-09-12",
    "sampling+": "2011-09-12",
}
UNITS_DEED_ONLY = [
    "mark",
    "publicdomain",
]


class LegalCodeQuerySet(models.QuerySet):
    # We'll create LegalCode and License objects for all the by licenses,
    # and the zero_1.0 ones.
    # We're just doing these units and versions for now:
    # by* 4.0
    # by* 3.0 - including ported
    # cc 1.0

    # Queries for LegalCode objects
    LICENSES_ALL_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
    )
    LICENSES_40_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="4.0",
    )
    LICENSES_30_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="3.0",
    )
    LICENSES_25_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="2.5",
    )
    LICENSES_21_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="2.1",
    )
    LICENSES_20_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="2.0",
    )
    LICENSES_10_QUERY = Q(
        license__unit__in=UNITS_LICENSES,
        license__version="1.0",
    )

    # All of the Public Domain declarations are at version 1.0
    PUBLIC_DOMAIN_ALL_QUERY = Q(license__unit__in=UNITS_PUBLIC_DOMAIN)

    PUBLIC_DOMAIN_ZERO_QUERY = Q(license__unit="zero")

    def translated(self):
        """
        Return a queryset of the LegalCode objects that we are doing the
        translation process on.
        """
        # Only the 4.0 Licenses 4.0 and CC0 1.0 currently have translation
        # support. TODO: add Licenses 3.0 IGO
        return self.filter(
            self.LICENSES_40_QUERY | self.PUBLIC_DOMAIN_ZERO_QUERY
        )

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
        help_text="Django langauge code (lowercase RFC5646 language tag)",
    )
    html_file = models.CharField(
        "HTML file",
        max_length=300,
        help_text="HTML file we got this from",
        blank=True,
        default="",
    )
    translation_last_update = models.DateTimeField(
        help_text="The last_updated field from Transifex for this translation",
        blank=True,
        null=True,
        default=None,
    )
    title = models.CharField(
        max_length=112,
        help_text="License title in this language, e.g."
        " 'Atribución/Reconocimiento 4.0 Internacional'",
        blank=True,
        default="",
    )
    html = models.TextField("HTML", blank=True, default="")
    legal_code_url = models.URLField("Legal Code URL", blank=True, default="")
    deed_url = models.URLField("Deed URL", unique=True)
    plain_text_url = models.URLField(
        "Plain text URL",
        blank=True,
        default="",
    )

    objects = LegalCodeQuerySet.as_manager()

    class Meta:
        ordering = ["license", "language_code"]

    def __str__(self):
        return f"LegalCode<{self.language_code}, {self.license}>"

    def save(self, *args, **kwargs):
        self.deed_url = build_path(
            self.license.canonical_url,
            "deed",
            self.language_code,
        )
        self.legal_code_url = build_path(
            self.license.canonical_url,
            "legalcode",
            self.language_code,
        )
        # NOTE: plaintext functionality disabled
        # unit = self.license.unit
        # if (
        #     (unit in UNITS_LICENSES and float(self.license.version) > 2.5)
        #     or unit == "zero"
        # ) and self.language_code == "en":
        #     self.plain_text_url = build_path(
        #         self.license.canonical_url,
        #         "legalcode.txt",
        #         self.language_code,
        #     )
        super().save(*args, **kwargs)

    def _get_save_path(self):
        """
        If saving the deed or license as a static file, this returns
        the relative path where the saved file should be, not including
        the actual filename.

        If saving the license as a static file, this returns the relative
        path of the file to save it as.

        ported Licenses 3.0 and earlier
            Formula
                CATEGORY/UNIT/VERSION/JURISDICTION
            Examples
                licenses/by/3.0/am
                licenses/by-nc/3.0/pl
                licenses/by-nc-nd/2.5/au
                licenses/by-nc-sa/2.5/ch
                licenses/by/2.1/es
                licenses/by-nc/2.1/jp
                licenses/by/2.0/kr
                licenses/nd-nc/1.0/fi

        unported Licenses 3.0, Licenses 4.0, and Public Domain:
            Formula
                CATEGORY/UNIT/VERSION
            Examples
                publicdomain/zero/1.0
                licenses/by-nc-nd/4.0/
                licenses/by-nc-sa/4.0/
                licenses/by-nc/4.0/
                licenses/by-nd/4.0/
                licenses/by-sa/4.0/
                licenses/by/4.0/
        """

        license = self.license
        unit = license.unit.lower()
        if license.jurisdiction_code:
            # ported Licenses 3.0 and earlier
            return os.path.join(
                license.category,  # licenses or publicdomain
                unit,  # ex. by, by-nc-nd
                license.version,  # ex. 1.0, 2.0
                license.jurisdiction_code,  # ex. ca, tw
            )
        else:
            # unported Licenses 3.0, Licenses 4.0, and Public Domain:
            return os.path.join(
                license.category,  # licenses or  publicdomain
                unit,  # ex. by, by-nc-nd, zero
                license.version,  # ex. 1.0, 4.0
            )

    def get_file_and_links(self, document):
        """
        1. Add document type ("deed" or "legalcode"), language, and HTML file
           extension to filename to save content to.
        2. Generate list of symlinks to ensure expected URLs function
           correctly.
        """
        license = self.license
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
        we'll use to manage the modifications?  Basically its
        "{unit}-{version}-{language}-{jurisdiction code}", except that all the
        "by* 4.0" licenses use "cc4" for the unit part. This has to be a valid
        DNS domain, so we also change any _ to - and remove any periods.
        """
        license = self.license
        parts = []
        if license.unit.startswith("by") and license.version == "4.0":
            parts.append("cc4")
        else:
            parts.extend([license.unit, license.version])
        parts.append(self.language_code)
        if license.jurisdiction_code:
            parts.append(license.jurisdiction_code)
        return "-".join(parts).replace("_", "-").replace(".", "").lower()

    def identifier(self):
        """
        Returns e.g. 'CC BY-SA 4.0' - all upper case etc. No language.
        """
        return self.license.identifier()

    @property
    def translation_domain(self):
        return self.license.resource_slug

    def get_translation_object(self):
        domain = self.license.resource_slug
        return get_translation_object(
            django_language_code=self.language_code,
            domain=domain,
        )

    def get_pofile(self) -> polib.POFile:
        with open(self.translation_filename(), "rb") as f:
            content = f.read()
        return polib.pofile(content.decode(), encoding="utf-8")

    def get_english_pofile_path(self) -> str:
        if self.language_code != DEFAULT_LANGUAGE_CODE:
            # Same license, just in English translation:
            english_legal_code = self.license.get_legal_code_for_language_code(
                DEFAULT_LANGUAGE_CODE
            )
            return english_legal_code.translation_filename()
        return self.translation_filename()

    def translation_filename(self):
        """
        Return absolute path to the .po file with this translation.
        These are in the cc-licenses-data repository, in subdirectories:
          - "legalcode/"
          - language code
          - "LC_MESSAGES/"  (Django insists on this)
          - files

        The filenames are {resource_slug}.po (get the resource_slug
        from the license).

        e.g. for the BY-NC 4.0 French translation, which has no jurisdiction,
        the filename will be "by-nc_4.0.po", and in full,
        "{translation repo topdir}/legalcode/fr/by-nc_4.0.po".
        """
        filename = f"{self.license.resource_slug}.po"
        fullpath = os.path.abspath(
            os.path.realpath(
                os.path.join(
                    settings.DATA_REPOSITORY_DIR,
                    "legalcode",
                    self.language_code,
                    "LC_MESSAGES",
                    filename,
                )
            )
        )
        return fullpath


class License(models.Model):
    canonical_url = models.URLField(
        "Canonical URL",
        max_length=200,
        help_text="The license's unique identifier, e.g."
        " 'https://creativecommons.org/licenses/by-nd/2.0/br/'",
        unique=True,
    )
    unit = models.CharField(
        max_length=20,
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
    jurisdiction_code = models.CharField(
        max_length=9,
        blank=True,
        default="",
    )
    creator_url = models.URLField(
        "Creator URL",
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
    source = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="source_of",
        help_text="another license that this is the translation of",
    )
    is_replaced_by = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="replaces",
        help_text="another license that has replaced this one",
    )
    is_based_on = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
        related_name="base_of",
        help_text="another license that this one is based on",
    )
    deprecated_on = models.DateField(
        blank=True,
        null=True,
        default=None,
        help_text="if set, the date on which this license was deprecated",
    )

    deed_only = models.BooleanField(default=False)

    permits_derivative_works = models.BooleanField(default=None)
    permits_reproduction = models.BooleanField(default=None)
    permits_distribution = models.BooleanField(default=None)
    permits_sharing = models.BooleanField(default=None)

    requires_share_alike = models.BooleanField(default=None)
    requires_notice = models.BooleanField(default=None)
    requires_attribution = models.BooleanField(default=None)
    requires_source_code = models.BooleanField(default=None)

    prohibits_commercial_use = models.BooleanField(default=None)
    prohibits_high_income_nation_use = models.BooleanField(default=None)

    class Meta:
        ordering = ["-version", "unit", "jurisdiction_code"]

    def __str__(self):
        return (
            f"License<{self.unit},{self.version}," f"{self.jurisdiction_code}>"
        )

    def get_metadata(self):
        """
        Return a dictionary with the metadata for this license.
        """
        language_default = get_default_language_for_jurisdiction(
            self.jurisdiction_code
        )
        data = {}
        default_lc = self.legal_codes.filter(language_code=language_default)[0]
        data["canonical_url"] = self.canonical_url
        data["deed_only"] = self.deed_only
        if self.deprecated_on:
            data["deprecated_on"] = self.deprecated_on
        if self.jurisdiction_code:
            data["jurisdiction_code"] = self.jurisdiction_code
        data["jurisdiction_name"] = get_jurisdiction_name(
            self.category,
            self.unit,
            self.version,
            self.jurisdiction_code,
        )
        data["identifier"] = self.identifier()
        if not self.deed_only:
            data["legal_code_languages"] = {}
            for lc in self.legal_codes.order_by("language_code"):
                lang_code = lc.language_code
                language_info = translation.get_language_info(lang_code)
                data["legal_code_languages"][lang_code] = language_info["name"]
        data["permits_derivative_works"] = self.permits_derivative_works
        data["permits_distribution"] = self.permits_distribution
        data["permits_reproduction"] = self.permits_reproduction
        data["permits_sharing"] = self.permits_sharing
        data["prohibits_commercial_use"] = self.prohibits_commercial_use
        data[
            "prohibits_high_income_nation_use"
        ] = self.prohibits_high_income_nation_use
        data["requires_attribution"] = self.requires_attribution
        data["requires_notice"] = self.requires_notice
        data["requires_share_alike"] = self.requires_share_alike
        data["requires_source_code"] = self.requires_source_code
        data["title"] = default_lc.title
        data["unit"] = self.unit
        data["version"] = self.version
        return data

    def logos(self):
        """
        Return an iterable of the codes for the logos that should be
        displayed with this license. E.g.:
        ["cc-logo", "cc-zero", "cc-by"]
        """
        result = ["cc-logo"]  # Everybody gets this
        if self.unit == "zero":
            result.append("cc-zero")
        elif self.unit.startswith("by"):
            result.append("cc-by")
            if self.prohibits_commercial_use:
                result.append("cc-nc")
            if self.requires_share_alike:
                result.append("cc-sa")
            if not self.permits_derivative_works:
                result.append("cc-nd")
        return result

    def get_legal_code_for_language_code(self, language_code):
        """
        Return the LegalCode object for this license and language.
        """
        if not language_code:
            language_code = translation.get_language()
        try:
            return self.legal_codes.get(language_code=language_code)
        except LegalCode.DoesNotExist as e:
            e.args = (f"{e.args[0]} language_code={language_code}",)
            raise

    @property
    def resource_name(self):
        """Human-readable name for the translation resource for this license"""
        return self.identifier()

    @property
    def resource_slug(self):
        # Transifex translation resource slug for this license.
        # letters, numbers, underscores or hyphens.
        # No periods.
        # All lowercase.
        if self.jurisdiction_code:
            slug = f"{self.unit}_{self.version}_{self.jurisdiction_code}"
        else:
            slug = f"{self.unit}_{self.version}"
        slug = slug.replace(".", "")
        slug = slug.lower()
        return slug

    def rdf(self):
        """Generate RDF for this license?"""
        return "RDF Generation Not Implemented"  # FIXME if needed

    def identifier(self):
        """
        Returns e.g. 'CC BY-SA 4.0' - all upper case etc. No language.
        """
        license = self
        identifier = f"{license.unit} {license.version}"

        if license.unit == "mark":
            identifier = f"PDM {license.version}"
        elif license.unit == "zero":
            identifier = f"CC0 {license.version}"
        elif license.unit in UNITS_LICENSES:
            identifier = f"CC {identifier}"

        if license.jurisdiction_code:
            identifier = f"{identifier} {license.jurisdiction_code}"
        identifier = identifier.upper()
        return identifier

    @property
    def level_of_freedom(self):
        if self.unit in ("devnations", "sampling"):
            return FREEDOM_LEVEL_MIN
        elif (
            self.unit.find("sampling") > -1
            or self.unit.find("nc") > -1
            or self.unit.find("nd") > -1
        ):
            return FREEDOM_LEVEL_MID
        else:
            return FREEDOM_LEVEL_MAX

    @property
    def superseded(self):
        return self.is_replaced_by is not None

    @property
    def sampling_plus(self):
        return self.unit in ("nc-sampling+", "sampling+")

    @property
    def include_share_adapted_material_clause(self):
        return self.unit in ["by", "by-nc"]

    # TODO: update as part of translation rewrite
    # def tx_upload_messages(self):
    #     """
    #     Upload the messages to Transifex,
    #     creating the resource if it doesn't already exist.
    #     """
    #     # Have to do English first, they get uploaded differently as the
    #     # "source" messages and are required if we need to first create the
    #     # resource in Transifex.
    #     en_legal_code = self.get_legal_code_for_language_code(
    #         DEFAULT_LANGUAGE_CODE
    #     )
    #     helper = TransifexHelper()
    #     helper.upload_messages_to_transifex(legal_code=en_legal_code)
    #     for legal_code in self.legal_codes.exclude(
    #         language_code=DEFAULT_LANGUAGE_CODE
    #     ):
    #         helper.upload_messages_to_transifex(legal_code=legal_code)

    @property
    def nc(self):
        return "nc" in self.unit

    @property
    def nd(self):
        return "nd" in self.unit

    @property
    def sa(self):
        return "sa" in self.unit


class TranslationBranch(models.Model):
    branch_name = models.CharField(max_length=40)
    legal_codes = models.ManyToManyField("LegalCode")
    version = models.CharField(
        max_length=3,
        help_text="E.g. '4.0'. Not required.",
        blank=True,
        default="",
    )
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="Django langauge code (lowercase RFC5646 language tag)",
    )
    last_transifex_update = models.DateTimeField(
        "Time when last updated on Transifex.",
        blank=True,
        null=True,
        default=None,
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
        for code in self.legal_codes.all():
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


def build_path(canonical_url, document, language_code):
    path = canonical_url.replace("https://creativecommons.org", "")
    if document == "legalcode.txt" or not language_code:
        path = posixpath.join(path, document)
    else:
        path = posixpath.join(path, f"{document}.{language_code}")
    return path
