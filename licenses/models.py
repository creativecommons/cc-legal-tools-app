"""
Every license can be identified by a URL, e.g. "http://creativecommons.org/licenses/by-nc-sa/4.0/"
or "http://creativecommons.org/licenses/by-nc-nd/2.0/tw/".  In the RDF, this is the rdf:about
attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation of the license
with the url in the dc:source's rdf:resource attribute.

Some licenses ahve a dcq:isReplacedBy element.

"""
from django.db import models
from django.urls import reverse

from i18n import DEFAULT_JURISDICTION_LANGUAGES, DEFAULT_LANGUAGE_CODE
from licenses import FREEDOM_LEVEL_MAX, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MIN

MAX_LANGUAGE_CODE_LENGTH = 8


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

    class Meta:
        ordering = ["license__about"]

    def __str__(self):
        return f"LegalCode<{self.language_code}, {self.license.about}>"


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

    @property
    def translation_domain(self):
        # If there's any - or _ in the domain, things get confusing.
        # Just do letters and digits.
        if self.jurisdiction_code:
            domain = f"{self.license_code}{self.version}{self.jurisdiction_code}"
        else:
            domain = f"{self.license_code}{self.version}"
        return domain.replace("-", "").replace("_", "").replace(".", "")

    def rdf(self):
        """Generate RDF for this license?"""
        return "RDF Generation Not Implemented"  # FIXME if needed

    def translated_title(self, language_code=None):
        return "FIXME: Implement translated title"
        # if not language_code:
        #     # Use current language
        #     language_code = translation.get_language()
        #
        # with activate_domain_language(self.translation_domain, language_code):
        #     # We're going to create a 'translation' for a fake locale named
        #     # `lang_plus_domain`, then temporarily activate it and translate
        #     # the key we use for medium license titles in our message files.
        #     return gettext(f"license_medium")

    def default_language_code(self):
        if (
            self.jurisdiction_code
            and self.jurisdiction_code in DEFAULT_JURISDICTION_LANGUAGES
            and len(DEFAULT_JURISDICTION_LANGUAGES[self.jurisdiction_code]) == 1
        ):
            return DEFAULT_JURISDICTION_LANGUAGES[self.jurisdiction_code][0]
        return DEFAULT_LANGUAGE_CODE

    def get_deed_url_for_language(self, target_lang: str):
        """
        Return a URL that'll give us a view for a deed for this license,
        displayed in the specified language. (If you want it displayed in
        a default language, use get_deed_url()).
        """
        kwargs = dict(
            license_code=self.license_code,
            version=self.version,
            target_lang=target_lang,
        )

        if self.jurisdiction_code:
            kwargs["jurisdiction"] = self.jurisdiction_code
            viewname = "license_deed_view_code_version_jurisdiction_language"
        else:
            viewname = "license_deed_view_code_version_language"

        return reverse(viewname, kwargs=kwargs)

    def get_deed_url(self):
        """
        Return a URL that'll give us a view for the deed for this license,
        but leave the language up to the view.
        """
        kwargs = dict(license_code=self.license_code, version=self.version,)

        if self.jurisdiction_code:
            kwargs["jurisdiction"] = self.jurisdiction_code
            viewname = "license_deed_view_code_version_jurisdiction"
        else:
            viewname = "license_deed_view_code_version_english"

        return reverse(viewname, kwargs=kwargs)

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


class TranslatedLicenseName(models.Model):
    license = models.ForeignKey(License, related_name="names", on_delete=models.CASCADE)
    language_code = models.CharField(
        max_length=MAX_LANGUAGE_CODE_LENGTH,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?",
    )
    name = models.CharField(max_length=250, help_text="Translated name of license")

    class Meta:
        unique_together = [
            ("license", "language_code"),
        ]

    def __str__(self):
        return f"TranslatedLicenseName<{self.language_code}, {self.license}>"


class LicenseLogo(models.Model):
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    image = models.FileField()

    def __str__(self):
        return f"LicenseLogo<{self.image.url}>"
