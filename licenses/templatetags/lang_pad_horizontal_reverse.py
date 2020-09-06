from django import template

register = template.Library()

@register.simple_tag
def lang_pad_horizontal_reverse(is_rtl):
    """Adjust padding right or left based on language direction.

    Notes: 
        Padding direction is the reverse of lang_pad_horizontal
    Parameter(s):
        - is_rtl - (boolean) whether or not the langauge of the 
                 - of the template is a right to left language
    """
    return 'right' if not is_rtl else 'left'
