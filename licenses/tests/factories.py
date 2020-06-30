import factory
import factory.fuzzy
from django.utils import translation
from factory import post_generation

from licenses.models import (
    License,
    LegalCode,
    Creator,
    Jurisdiction,
    LicenseClass,
    Language,
    TranslatedLicenseName,
    LicenseLogo,
)


class CreatorFactory(factory.DjangoModelFactory):
    class Meta:
        model = Creator

    url = factory.Faker("url")


class JurisdictionFactory(factory.DjangoModelFactory):
    class Meta:
        model = Jurisdiction

    url = factory.Faker("url")


class LanguageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Language

    code = factory.fuzzy.FuzzyChoice(["en", "sr-Latn", "x-i18n"])


class LegalCodeFactory(factory.DjangoModelFactory):
    class Meta:
        model = LegalCode

    url = factory.Faker("url")


class LicenseClassFactory(factory.DjangoModelFactory):
    class Meta:
        model = LicenseClass

    url = factory.Faker("url")


class LicenseFactory(factory.DjangoModelFactory):
    class Meta:
        model = License

    about = factory.Faker("url")
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
    jurisdiction = factory.SubFactory(JurisdictionFactory)

    @post_generation
    def post(obj, create, extracted, **kwargs):
        if not obj.names.count():
            TranslatedLicenseNameFactory(license=obj, language__code=translation.get_language())


class LicenseLogoFactory(factory.DjangoModelFactory):
    class Meta:
        model = LicenseLogo

    license = factory.SubFactory(LicenseFactory)
    image = factory.Faker("name")


class TranslatedLicenseNameFactory(factory.DjangoModelFactory):
    class Meta:
        model = TranslatedLicenseName

    license = factory.SubFactory(LicenseFactory)
    language = factory.SubFactory(LanguageFactory)
    name = factory.Faker("name")
