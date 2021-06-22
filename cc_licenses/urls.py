"""cc_licenses URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  re_path(r'^blog/', include(blog_urls))
"""
# Third-party
from django.conf import settings
from django.conf.urls import re_path
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

# First-party/Local
from licenses.views import (
    view_branch_status,
    view_dev_home,
    view_page_not_found,
    view_translation_status,
)


def custom_page_not_found(request):
    return view_page_not_found(request, None)


urlpatterns = [
    path("", RedirectView.as_view(url="dev/")),
    path(
        "dev/",
        view_dev_home,
        name="dev_home",
    ),
    path("dev/admin/", admin.site.urls, name="dev_admin"),
    re_path(
        r"^dev/status/(?P<id>\d+)/$",
        view_branch_status,
        name="branch_status",
    ),
    re_path(
        r"^dev/status/$",
        view_translation_status,
        name="translation_status",
    ),
    path(
        "dev/404",
        custom_page_not_found,
        name="dev_404",
    ),
    path("", include("licenses.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = "licenses.views.view_page_not_found"


if settings.DEBUG:
    # Third-party
    import debug_toolbar

    urlpatterns += [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ]
