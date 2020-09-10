"""
'cctrans' template tag library for Creative Commons license translation

https://www.caktusgroup.com/blog/2017/05/01/building-custom-block-template-tag/
"""
from django import template
from django.conf import settings
from django.template.base import FilterExpression, kwarg_re
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe


register = template.Library()

@register.filter
@stringfilter
def t(value, translations):
    return mark_safe(translations.translate(value))


def parse_tag(token, parser):
    """
    Generic template tag parser.

    Returns a three-tuple: (tag_name, args, kwargs)

    tag_name is a string, the name of the tag.

    args is a list of FilterExpressions, from all the arguments that didn't look like kwargs,
    in the order they occurred, including any that were mingled amongst kwargs.

    kwargs is a dictionary mapping kwarg names to FilterExpressions, for all the arguments that
    looked like kwargs, including any that were mingled amongst args.

    (At rendering time, a FilterExpression f can be evaluated by calling f.resolve(context).)
    """
    # Split the tag content into words, respecting quoted strings.
    bits = token.split_contents()

    # Pull out the tag name.
    tag_name = bits.pop(0)

    # Parse the rest of the args, and build FilterExpressions from them so that
    # we can evaluate them later.
    args = []
    kwargs = {}
    for bit in bits:
        # Is this a kwarg or an arg?
        match = kwarg_re.match(bit)
        kwarg_format = match and match.group(1)
        if kwarg_format:
            key, value = match.groups()
            kwargs[key] = FilterExpression(value, parser)
        else:
            args.append(FilterExpression(bit, parser))

    return (tag_name, args, kwargs)

# @register.simple_tag(takes_context=True)
# def t(context, msgid):
#     translation = context["translation"]
#     return translation.translate(msgid)


class SimpleTranslateNode(template.Node):
    def __init__(self, arg):
        self.arg = arg
    def render(self, context):
        translation = context["translation"]
        # arg is a FilterExpression
        msgid = self.arg.resolve(context)
        content = translation.translate(msgid)
        # if settings.DEBUG:
        #     # Underline translated text so it stands out
        #     content = f"<u>{content}</u>"
        content = mark_safe(content)
        return content

def do_t(parser, token):
    tag_name, args, kwargs = parse_tag(token, parser)
    return SimpleTranslateNode(args[0])

register.tag("t", do_t)
