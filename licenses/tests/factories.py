# Third-party
import factory.fuzzy

# First-party/Local
from licenses.models import LegalCode, License, TranslationBranch

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


class LicenseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = License

    about = factory.Faker("url")
    license_code = factory.fuzzy.FuzzyChoice(
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
    license_class_url = factory.Faker("url")


class LegalCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalCode

    language_code = factory.fuzzy.FuzzyChoice(language_codes)
    license = factory.SubFactory(LicenseFactory)


class TranslationBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TranslationBranch

    language_code = factory.fuzzy.FuzzyChoice(language_codes)
    version = "4.0"
    branch_name = factory.LazyAttribute(
        lambda o: f"cc4-{o.language_code}".lower().replace("_", "-")
    )

    @factory.post_generation
    def legalcodes(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of legalcodes were passed in, use them
            for group in extracted:
                self.legalcodes.add(group)
        else:
            # Generate a random one with the right features
            self.legalcodes.add(
                LegalCodeFactory(
                    language_code=self.language_code,
                    license__version=self.version,
                )
            )
