"""
Every license can be identified by a URL, e.g. "http://creativecommons.org/licenses/by-nc-sa/4.0/"
or "http://creativecommons.org/licenses/by-nc-nd/2.0/tw/".  In the RDF, this is the rdf:about
attribute on the cc:License element.

If a license has a child dc:source element, then this license is a translation of the license
with the url in the dc:source's rdf:resource attribute.

Some licenses ahve a dcq:isReplacedBy element.

"""
import urllib

from django.db import models
from django.utils import translation

from licenses import FREEDOM_LEVEL_MIN, FREEDOM_LEVEL_MID, FREEDOM_LEVEL_MAX


class Creator(models.Model):
    url = models.URLField(max_length=200, help_text="E.g. http://creativecommons.org",)

    def __str__(self):
        return self.url


class Jurisdiction(models.Model):
    url = models.URLField(
        max_length=200, help_text="E.g. http://creativecommons.org/international/at/",
    )
    # FIXME: Where to get data on jurisdictions' default languages?
    default_language = models.ForeignKey(
        "Language", null=True, on_delete=models.CASCADE
    )

    @property
    def code(self):
        pieces = urllib.parse.urlsplit(self.url).path.strip("/").split("/")
        try:
            return pieces[1]
        except IndexError:
            return ""

    def __str__(self):
        return self.url


class LicenseClass(models.Model):
    # <cc:licenseClass rdf:resource="http://creativecommons.org/license/"/>
    url = models.URLField(
        max_length=200, help_text="E.g. http://creativecommons.org/license/",
    )

    def __str__(self):
        return self.url


class Language(models.Model):
    code = models.CharField(
        max_length=7,
        help_text="E.g. 'en', 'en-ca', 'sr-Latn', or 'x-i18n'. Case-sensitive?",
    )

    def __str__(self):
        return self.code


class LegalCode(models.Model):
    url = models.URLField(
        max_length=200,
        help_text="E.g. http://creativecommons.org/licenses/by-nd/3.0/rs/legalcode.sr-Cyrl",
    )
    language = models.ForeignKey(Language, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.url


class License(models.Model):
    about = models.URLField(
        max_length=200,
        help_text="The license's unique identifier, e.g. 'http://creativecommons.org/licenses/by-nd/2.0/br/'",
        unique=True,
    )
    license_code = models.CharField(
        max_length=40,
        help_text="shorthand representation for which class of licenses this falls into.  E.g. 'by-nc-sa', or 'MIT'",
    )
    version = models.CharField(
        max_length=3, help_text="E.g. '4.0'. Not required.", blank=True, default=""
    )
    legalcodes = models.ManyToManyField(
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
        return self.about

    def set_permissions_and_prohibitions_from_license_code(self):
        if self.creator and self.creator.url == "http://creativecommons.org":
            self.requires_share_alike = "sa" in self.license_code
            self.permits_derivative_works = "nd" not in self.license_code
        else:
            raise ValueError("set_permissions_and_prohibitions_from_license_code should only be called on CC licenses")

    def rdf(self):
        """Generate RDF for this license?"""
        return "RDF Generation Not Implemented"  # FIXME if needed

    def translated_title(self, language_code=None):
        if not language_code:
            # Use current language
            language_code = translation.get_language()
        translated_license_name = self.names.get(language__code=language_code)
        return translated_license_name.name

    def legalcodes_for_language(self, target_lang: str):
        """Returns queryset of LegalCode"""
        return self.legalcodes.filter(language__code=target_lang)

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


class TranslatedLicenseName(models.Model):
    license = models.ForeignKey(License, related_name="names", on_delete=models.CASCADE)
    language = models.ForeignKey(Language, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=250, help_text="Translated name of license")

    def __str__(self):
        return self.name


class LicenseLogo(models.Model):
    license = models.ForeignKey(License, on_delete=models.CASCADE)
    image = models.FileField()

    def __str__(self):
        return self.image.url
