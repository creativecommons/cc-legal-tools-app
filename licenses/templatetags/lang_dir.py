from django import template

register = template.Library()


@register.simple_tag
def lang_dir(is_rtl):
    """Adjusts the direction of html elements based on whether
    or not the language in context is a left to right or right
    to left language.


    Parameter(s):
         - is_rtl - (boolean) whether or not the langauge of the
                  - of the template is a right to left language
    """
    return 'ltr' if not is_rtl else 'rtl'
