"""cc_licenses URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django_distill import distill_path, distill_url

from licenses.models import TranslationBranch
from licenses.views import branch_status, home, translation_status


def distill_no_parameters():
    return None


def distill_translation_branch_ids():
    """Return a list of dictionaries with the 'id' values for the translation branches"""
    return list(TranslationBranch.objects.filter(complete=False).values_list("id"))


urlpatterns = [
    url(r"^admin/", admin.site.urls),
    distill_path("", home, name="home", distill_func=distill_no_parameters),
    distill_url(
        r"status/(?P<id>\d+)/$",
        branch_status,
        name="branch_status",
        distill_func=distill_translation_branch_ids,
    ),
    distill_url(
        r"status/$",
        translation_status,
        name="translation_status",
        distill_func=distill_no_parameters,
    ),
    url(r"licenses/", include("licenses.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r"^__debug__/", include(debug_toolbar.urls)),
    ]
