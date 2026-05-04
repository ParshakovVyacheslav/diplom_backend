from django.conf import settings
from djoser import email


class ActivationEmail(email.ActivationEmail):
    template_name = 'email/activation.html'

    def get_context_data(self):
        context = super().get_context_data()
        context['protocol'] = getattr(settings, 'DJANGO_PUBLIC_URL_SCHEME', 'http')
        return context