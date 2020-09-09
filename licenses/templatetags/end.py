from django import template

register = template.Library()


@register.simple_tag
def end(is_rtl):
    """Returns 'right' if ltr language or 'left' if rtl language

    Parameter(s):
        - is_rtl - (boolean) whether or not the langauge of the
                 - of the template is a right to left language
    """
    return 'right' if not is_rtl else 'left'
