from django.urls import path

from .views import LicenseView

urlpatterns = [
    path('', LicenseView.as_view(), name='licenses'),
]