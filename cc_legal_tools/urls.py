# Third-party
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

# First-party/Local
from legal_tools.views import view_page_not_found


def custom_page_not_found(request):
    return view_page_not_found(request, None)


urlpatterns = [
    path(
        "admin/",
        admin.site.urls,
        name="dev_admin",
    ),
    path(
        "error_404/",
        custom_page_not_found,
        name="error_404",
    ),
    path("", include("legal_tools.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = "legal_tools.views.view_page_not_found"


if settings.DEBUG:
    # Third-party
    import debug_toolbar

    urlpatterns += [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ]
