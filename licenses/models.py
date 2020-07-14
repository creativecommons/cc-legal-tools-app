"""
Every license can be identified by a URL, e.g. "http://creativecommons.org/licenses/by-nc-sa/4.0/"
or "http://creativecommons.org/licenses/by-nc-nd/2.0/tw/".  In the RDF, this is the rdf:about
attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation of the license
with the url in the dc:source's rdf:resource attribute.

Some licenses ahve a dcq:isReplacedBy element.

"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import translation
from django.utils.translation import ugettext

from i18n import DEFAULT_LANGUAGE_CODE
from licenses import (
    FREEDOM_LEVEL_MIN,
    FREEDOM_LEVEL_MID,
    FREEDOM_LEVEL_MAX,
)


class Creator(models.Model):
    url = models.URLField(
        unique=True, max_length=200, help_text="E.g. http://creativecommons.org"
    )

    def __str__(self):
        return f"Creator<{self.url}>"


class Jurisdiction(models.Model):
    code = models.CharField(max_length=9, unique=True, blank=False)

    @property
    def about(self):
        # Not using "https:" deliberately because this is the "official"
        # name of the jurisdiction in the RDF.
        return f"http://creativecommons.org/international/{self.code}/"

    default_language = models.ForeignKey(
        "Language", null=True, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Jurisdiction<{self.code}>"


class LicenseClass(models.Model):
    # <cc:licenseClass rdf:resource="http://creativecommons.org/license/"/>
    url = models.URLField(
        unique=True,
        max_length=200,
        help_text="E.g. http://creativecommons.org/license/",
    )

    def __str__(self):
        return f"LicenseClass<{self.url}>"


class Language(models.Model):
    code = models.CharField(
        unique=True,
        max_length=7,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?",
    )

    def __str__(self):
        return f"Language<{self.code}>"

    def name(self):
        """Name of language (translated to current active language)"""
        name = dict(settings.LANGUAGES)[self.code]
        return ugettext(name)


class LegalCode(models.Model):
    url = models.URLField(
        max_length=200,
        help_text="E.g. http://creativecommons.org/licenses/by-nd/3.0/rs/legalcode.sr-Cyrl",
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE)

    class Meta:
        unique_together = [
            ("url", "language"),
        ]

    def __str__(self):
        return f"LegalCode<{self.language}, {self.url}>"


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
    legal_codes = models.ManyToManyField(
        LegalCode,
        blank=True,
        help_text="legal codes related to this license? not sure what these are though",
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="licenses",
        help_text="Jurisdiction of this license",
    )
    creator = models.ForeignKey(
        Creator,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="licenses",
        help_text="Creator of this license.",
    )
    license_class = models.ForeignKey(
        LicenseClass,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="licenses",
        help_text="Which license class this license belongs to.",
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

    def __str__(self):
        return f"License<{self.about}>"

    def rdf(self):
        """Generate RDF for this license?"""
        return "RDF Generation Not Implemented"  # FIXME if needed

    def translated_title(self, language_code=None):
        if not language_code:
            # Use current language
            language_code = translation.get_language()
        try:
            translated_license_name = self.names.get(language__code=language_code)
        except TranslatedLicenseName.DoesNotExist:
            if language_code != DEFAULT_LANGUAGE_CODE:
                return self.translated_title(DEFAULT_LANGUAGE_CODE)
            return self.about
        return translated_license_name.name

    def default_language_code(self):
        if self.jurisdiction and self.jurisdiction.default_language:
            return self.jurisdiction.default_language.code
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

        if self.jurisdiction:
            kwargs["jurisdiction"] = self.jurisdiction.code
            viewname = "license_deed_view_code_version_jurisdiction_language"
        else:
            viewname = "license_deed_view_code_version_language"

        return reverse(viewname, kwargs=kwargs)

    def get_deed_url(self):
        """
        Return a URL that'll give us a view for the deed for this license,
        but leave the language up to the view.
        """
        kwargs = dict(
            license_code=self.license_code,
            version=self.version,
        )

        if self.jurisdiction:
            kwargs["jurisdiction"] = self.jurisdiction.code
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
        return self.license_code in ('nc-sampling+', 'sampling+')


class TranslatedLicenseName(models.Model):
    license = models.ForeignKey(License, related_name="names", on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=250, help_text="Translated name of license")

    class Meta:
        unique_together = [
            ("license", "language"),
        ]

    def __str__(self):
        return f"TranslatedLicenseName<{self.language}, {self.license}>"


class LicenseLogo(models.Model):
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    image = models.FileField()

    def __str__(self):
        return f"LicenseLogo<{self.image.url}>"
