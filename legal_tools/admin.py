# Third-party
from django.contrib import admin

# First-party/Local
from legal_tools.models import LegalCode, Tool, TranslationBranch


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
        "tool",
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
        "tool",
    ]
    list_filter = [
        "tool__unit",
        "tool__version",
        "language_code",
    ]
    raw_id_fields = [
        "tool",
    ]


class LegalCodeInline(admin.TabularInline):
    model = LegalCode
    list_display = [
        "url",
        "language_code",
        "tool",
    ]


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    fields = [
        "base_url",
        "unit",
        "version",
        "spdx_identifier",
        "creator_url",
        "category",
        "jurisdiction_code",
        "source",
        "is_replaced_by",
        "deprecated_on",
        "permits_derivative_works",
        "permits_reproduction",
        "permits_distribution",
        "permits_sharing",
        "requires_share_alike",
        "requires_notice",
        "requires_attribution",
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
    ]
    search_fields = [
        "unit",
        "version",
        "base_url",
    ]
