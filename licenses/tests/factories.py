import factory.fuzzy

from licenses.models import LegalCode, License


class LicenseFactory(factory.DjangoModelFactory):
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


class LegalCodeFactory(factory.DjangoModelFactory):
    class Meta:
        model = LegalCode

    language_code = "de"
    license = factory.SubFactory(LicenseFactory)
