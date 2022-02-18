# Third-party
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView

# First-party/Local
from legal_tools.views import view_page_not_found


def custom_page_not_found(request):
    return view_page_not_found(request, None)


urlpatterns = [
    # Redirect wp-content/ to static/wp-content/
    re_path(
        r"^(?P<wp_content>wp-content/.*)",
        RedirectView.as_view(url="/static/%(wp_content)s", permanent=False),
        name="static_wp_content_redirect",
    ),
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
