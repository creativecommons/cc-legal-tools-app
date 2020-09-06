from django import template

register = template.Library()

@register.simple_tag
def lang_pad_horizontal(is_rtl):
    """Adjust padding left or right based on language direction

    Parameter(s):
        - is_rtl - (boolean) whether or not the langauge of the 
                 - of the template is a right to left language
    """
    return 'left' if not is_rtl else 'right'
