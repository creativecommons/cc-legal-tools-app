import factory.fuzzy
from django.utils import translation
from factory import post_generation

from licenses.constants import LICENSE_VERSIONS
from licenses.models import (
    LegalCode,
    License,
    LicenseLogo,
    TranslatedLicenseName,
)


class LegalCodeFactory(factory.DjangoModelFactory):
    class Meta:
        model = LegalCode

    url = factory.Faker("url")
    language_code = "de"


class LicenseFactory(factory.DjangoModelFactory):
    class Meta:
        model = License

    about = factory.Faker("url")
    license_code = ""
    version = factory.fuzzy.FuzzyChoice(LICENSE_VERSIONS)
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

    @post_generation
    def post(obj, create, extracted, **kwargs):
        if not obj.names.count():
            TranslatedLicenseNameFactory(
                license=obj, language_code=translation.get_language()
            )


class LicenseLogoFactory(factory.DjangoModelFactory):
    class Meta:
        model = LicenseLogo

    license = factory.SubFactory(LicenseFactory)
    image = factory.Faker("name")


class TranslatedLicenseNameFactory(factory.DjangoModelFactory):
    class Meta:
        model = TranslatedLicenseName

    license = factory.SubFactory(LicenseFactory)
    language_code = "pt"
    name = factory.Faker("name")
