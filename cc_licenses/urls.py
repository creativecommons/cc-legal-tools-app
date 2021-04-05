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
# Third-party
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

# First-party/Local
from licenses.views import branch_status, translation_status

urlpatterns = [
    url(r"^admin/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    url(
        r"status/(?P<id>\d+)/$",
        branch_status,
        name="branch_status",
    ),
    url(
        r"status/$",
        translation_status,
        name="translation_status",
    ),
    url(r"licenses/", include("licenses.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # Third-party
    import debug_toolbar

    urlpatterns += [
        url(r"^__debug__/", include(debug_toolbar.urls)),
    ]
