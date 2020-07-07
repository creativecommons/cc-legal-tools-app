from django.contrib import admin

from licenses.models import License, LicenseClass, Language


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    pass


@admin.register(LicenseClass)
class LicenseClassAdmin(admin.ModelAdmin):
    pass


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    pass
