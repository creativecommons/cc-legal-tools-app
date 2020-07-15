from django.contrib import admin

from licenses.models import LegalCode, License


@admin.register(LegalCode)
class LegalCodeAdmin(admin.ModelAdmin):
    fields = [
        "url",
        "language_code",
    ]
    list_display = [
        "url",
        "language_code",
    ]
    list_filter = [
        "language_code",
    ]


class LegalCodeInline(admin.TabularInline):
    model = LegalCode


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
