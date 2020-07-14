from django.contrib import admin

from licenses.models import License, LicenseClass, Language, Jurisdiction


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_filter = [
        "license_code",
        "version",
        "creator__url",
        "license_class__url",
        "jurisdiction__code",
        "jurisdiction__default_language__code",
    ]


@admin.register(LicenseClass)
class LicenseClassAdmin(admin.ModelAdmin):
    pass


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    pass


@admin.register(Jurisdiction)
class JurisdictionAdmin(admin.ModelAdmin):
    list_display = ["code", "default_language"]
