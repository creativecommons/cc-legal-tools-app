# Standard library
import os.path

# Third-party
import factory

# First-party/Local
from legal_tools.models import (
    UNITS_LICENSES,
    UNITS_LICENSES_VERSIONS,
    UNITS_PUBLIC_DOMAIN,
    LegalCode,
    Tool,
    TranslationBranch,
)

# The language codes we already have translations for
LANGUAGE_CODES = [
    "ar",
    "cs",
    "de",
    "el",
    "en",
    "es",
    "eu",
    "fi",
    "fr",
    "hr",
    "id",
    "it",
    "ja",
    "ko",
    "kv",
    "lt",
    "mi",
    "nl",
    "no",
    "pl",
    "pt",
    "ro",
    "ru",
    "sl",
    "sv",
    "tr",
    "uk",
    "zh-hans",
    "zh-hant",
]


class ToolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tool

    category = factory.Faker(
        "random_element", elements=["licenses", "publicdomain"]
    )
    creator_url = factory.Faker("url")
    jurisdiction_code = ""
    permits_derivative_works = factory.Faker("pybool")
    permits_distribution = factory.Faker("pybool")
    permits_reproduction = factory.Faker("pybool")
    permits_sharing = factory.Faker("pybool")
    prohibits_commercial_use = factory.Faker("pybool")
    prohibits_high_income_nation_use = factory.Faker("pybool")
    requires_attribution = factory.Faker("pybool")
    requires_notice = factory.Faker("pybool")
    requires_share_alike = factory.Faker("pybool")
    unit = factory.Faker(
        "random_element",
        elements=UNITS_LICENSES + UNITS_PUBLIC_DOMAIN,
    )
    version = factory.Faker("random_element", elements=UNITS_LICENSES_VERSIONS)

    base_url = factory.LazyAttribute(
        lambda obj: os.path.join(
            obj.creator_url,
            obj.category,
            obj.unit,
            obj.version,
        )
    )


class LegalCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalCode

    language_code = factory.Faker("random_element", elements=LANGUAGE_CODES)
    tool = factory.SubFactory(ToolFactory)


class TranslationBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TranslationBranch

    language_code = factory.Faker("random_element", elements=LANGUAGE_CODES)
    version = "4.0"
    branch_name = factory.LazyAttribute(
        lambda obj: f"cc4-{obj.language_code}".lower().replace("_", "-")
    )

    @factory.post_generation
    def legal_codes(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of legal codes were passed in, use them
            for group in extracted:
                self.legal_codes.add(group)
        else:
            # Generate a random one with the right features
            self.legal_codes.add(
                LegalCodeFactory(
                    language_code=self.language_code,
                    tool__version=self.version,
                )
            )
