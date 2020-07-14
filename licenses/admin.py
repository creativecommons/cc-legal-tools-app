from django.contrib import admin

from licenses.models import License


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_filter = [
        "license_code",
        "version",
        "creator_url",
        "license_class_url",
        "jurisdiction_code",
    ]
