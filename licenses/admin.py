# Third-party
from django.contrib import admin

# First-party/Local
from licenses.models import LegalCode, License, TranslationBranch


@admin.register(TranslationBranch)
class TranslationBranchAdmin(admin.ModelAdmin):
    list_display = [
        "branch_name",
        "version",
        "language_code",
        "last_transifex_update",
        "complete",
    ]
    list_filter = [
        "complete",
        "version",
        "language_code",
    ]
    raw_id_fields = [
        "legalcodes",
    ]


@admin.register(LegalCode)
class LegalCodeAdmin(admin.ModelAdmin):
    fields = [
        "license",
        "language_code",
    ]
    list_display = [
        "language_code",
        "license",
    ]
    list_filter = [
        "language_code",
    ]
    raw_id_fields = [
        "license",
    ]


class LegalCodeInline(admin.TabularInline):
    model = LegalCode
    list_display = [
        "url",
        "language_code",
        "license",
    ]


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    fields = [
        "about",
        "license_code",
        "version",
        "creator_url",
        "license_class_url",
        "jurisdiction_code",
        "source",
        "is_replaced_by",
        "is_based_on",
        "deprecated_on",
        "permits_derivative_works",
        "permits_reproduction",
        "permits_distribution",
        "permits_sharing",
        "requires_share_alike",
        "requires_notice",
        "requires_attribution",
        "requires_source_code",
        "prohibits_commercial_use",
        "prohibits_high_income_nation_use",
    ]
    inlines = [LegalCodeInline]
    list_display = [
        "license_code",
        "title_english",
        "version",
        "jurisdiction_code",
    ]
    list_filter = [
        "license_code",
        "version",
        "creator_url",
        "license_class_url",
        "jurisdiction_code",
    ]
    raw_id_fields = [
        "source",
        "is_replaced_by",
        "is_based_on",
    ]
    search_fields = [
        "license_code",
        "version",
        "about",
    ]
