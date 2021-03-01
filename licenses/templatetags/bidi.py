# Third-party
from django import template
from django.utils.translation import get_language_bidi

register = template.Library()


@register.simple_tag
def start():
    """Returns 'left' if ltr language or 'right' if rtl language """
    return "right" if get_language_bidi() else "left"


@register.simple_tag
def end():
    """Returns 'right' if ltr language or 'left' if rtl language"""
    return "left" if get_language_bidi() else "right"
