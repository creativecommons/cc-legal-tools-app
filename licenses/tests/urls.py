from django.urls import path

from licenses.views import license_catcher


urlpatterns = [
    path(
        "<code:license_code>/<jurisdiction:jurisdiction>/<lang:target_lang>/",
        license_catcher,
        name="license_catcher"
    ),
    path(
        "<code:license_code>/<jurisdiction:jurisdiction>/",
        license_catcher,
        name="license_catcher_without_language",
        kwargs={
            "target_lang": ""
        }
    ),
]
