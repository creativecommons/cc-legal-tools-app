
from django.views.generic.base import TemplateView

from .models import License

class LicenseView(TemplateView):

    template_name = "licenses-detail.html"

    def get_context_data(self, **kwargs):
      context = super().get_context_data(**kwargs)
      context['license'] = License.objects.first()
      return context
