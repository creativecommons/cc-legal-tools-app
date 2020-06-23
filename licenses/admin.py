from django.contrib import admin

from licenses.models import License, LicenseClass


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    pass


@admin.register(LicenseClass)
class LicenseClassAdmin(admin.ModelAdmin):
    pass
