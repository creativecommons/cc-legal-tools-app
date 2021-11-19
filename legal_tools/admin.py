# Third-party
from django.contrib import admin

# First-party/Local
from legal_tools.models import LegalCode, License, TranslationBranch


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
        "legal_codes",
    ]


@admin.register(LegalCode)
class LegalCodeAdmin(admin.ModelAdmin):
    fields = [
        "title",
        "license",
        "language_code",
        "legal_code_url",
        "deed_url",
        # "plain_text_url",  # NOTE: plaintext functionality disabled
        "translation_last_update",
        "html_file",
        "html",
    ]
    list_display = [
        "language_code",
        "license",
    ]
    list_filter = [
        "license__unit",
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
        "canonical_url",
        "unit",
        "version",
        "creator_url",
        "category",
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
        "unit",
        "version",
        "jurisdiction_code",
    ]
    list_filter = [
        "unit",
        "version",
        "creator_url",
        "category",
        "jurisdiction_code",
    ]
    raw_id_fields = [
        "source",
        "is_replaced_by",
        "is_based_on",
    ]
    search_fields = [
        "unit",
        "version",
        "canonical_url",
    ]
