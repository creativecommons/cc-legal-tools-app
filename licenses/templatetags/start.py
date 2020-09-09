from django import template

register = template.Library()


@register.simple_tag
def start(is_rtl):
    """Returns 'left' if ltr language or 'right' if rtl language

    Parameter(s):
        - is_rtl - (boolean) whether or not the langauge of the
                 - of the template is a right to left language
    """
    return 'left' if not is_rtl else 'right'
