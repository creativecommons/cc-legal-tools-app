# Third-party
import factory.fuzzy

# First-party/Local
from legal_tools.models import LegalCode, Tool, TranslationBranch

# The language codes we already have translations for
language_codes = [
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
    "zh_Hans",
    "zh_Hant",
]


class ToolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tool

    base_url = factory.Faker("url")
    unit = factory.fuzzy.FuzzyChoice(
        ["by", "by-nc", "by-nc-nd", "by-nc-sa", "by-nd", "by-sa", "zero"]
    )
    version = factory.Faker("numerify", text="#.#")
    permits_derivative_works = factory.fuzzy.FuzzyChoice([False, True])
    permits_reproduction = factory.fuzzy.FuzzyChoice([False, True])
    permits_distribution = factory.fuzzy.FuzzyChoice([False, True])
    permits_sharing = factory.fuzzy.FuzzyChoice([False, True])
    requires_share_alike = factory.fuzzy.FuzzyChoice([False, True])
    requires_notice = factory.fuzzy.FuzzyChoice([False, True])
    requires_attribution = factory.fuzzy.FuzzyChoice([False, True])
    requires_source_code = factory.fuzzy.FuzzyChoice([False, True])
    prohibits_commercial_use = factory.fuzzy.FuzzyChoice([False, True])
    prohibits_high_income_nation_use = factory.fuzzy.FuzzyChoice([False, True])
    jurisdiction_code = ""
    creator_url = factory.Faker("url")
    category = factory.fuzzy.FuzzyChoice(["licenses", "publicdomain"])


class LegalCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalCode

    language_code = factory.fuzzy.FuzzyChoice(language_codes)
    tool = factory.SubFactory(ToolFactory)


class TranslationBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TranslationBranch

    language_code = factory.fuzzy.FuzzyChoice(language_codes)
    version = "4.0"
    branch_name = factory.LazyAttribute(
        lambda o: f"cc4-{o.language_code}".lower().replace("_", "-")
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
