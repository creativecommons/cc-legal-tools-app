import string
from threading import local

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# This is kind of gross, but it lets us simply produce
# a stream of letters and insert them into our template, without
# needing a for-loop or anything.

# Store state here. Use a thread-local so at least this is thread-safe.
next_letter_data = local()


@register.simple_tag
def home_box(license_code, version, language_code):
    from licenses.models import LegalCode

    result = []
    for legalcode in LegalCode.objects.filter(
        license__license_code=license_code,
        license__version=version,
        language_code=language_code,
    ):
        result.append(
            f"""<a href="{legalcode.deed_url()}">Deed</a> """
            f"""<a href="{legalcode.license_url()}">License</a>"""
        )
    return mark_safe("<br/>".join(result))


@register.simple_tag
def reset_letters(whichcase):
    """
    Reset the letter counts. After this,
    the next letter generated will be "a" again.
    """
    next_letter_data.index = 0
    if whichcase == "lowercase":
        next_letter_data.letters = string.ascii_lowercase
    elif whichcase == "uppercase":
        next_letter_data.letters = string.ascii_uppercase
    else:
        raise ValueError("Arg to reset_letters should be 'lowercase' or 'uppercase'")
    # Return value is inserted into the template, so return empty string.
    return ""


@register.simple_tag
def next_letter():
    """
    Return the next letter in sequence:
    "a", "b", "c", ...
    each time it's called after reset_letters()
    """
    next_letter = next_letter_data.letters[next_letter_data.index]
    next_letter_data.index += 1
    next_letter_data.current_letter = next_letter
    return next_letter


@register.simple_tag
def current_letter():
    """
    Return same letter that next_letter last returned.
    """
    return next_letter_data.current_letter


@register.filter
def is_one_of(legalcode, arg):
    codes = arg.split(",")
    return legalcode.license.license_code in codes


@register.simple_tag
def build_license_url(license_code, version, jurisdiction_code, language_code):
    """
    Return a URL to view the license specified by the inputs. Jurisdiction
    and language are optional.
    """
    # UGH. Is there any way we could do this with a simple url 'reverse'? The URL regex would
    # be complicated, but we have unit tests to determine if we've got it right.
    # See test_templatetags.py.
    if jurisdiction_code:
        if language_code == "en" or not language_code:
            return f"/licenses/{license_code}/{version}/{jurisdiction_code}/legalcode"
        else:
            return f"/licenses/{license_code}/{version}/{jurisdiction_code}/legalcode.{language_code}"
    else:
        if language_code == "en" or not language_code:
            return f"/licenses/{license_code}/{version}/legalcode"
        else:
            return f"/licenses/{license_code}/{version}/legalcode.{language_code}"


@register.simple_tag
def build_deed_url(license_code, version, jurisdiction_code, language_code):
    """
    Return a URL to view the deed specified by the inputs. Jurisdiction
    and language are optional.
    """
    # UGH. Is there any way we could do this with a simple url 'reverse'? The URL regex would
    # be complicated, but we have unit tests to determine if we've got it right.
    # See test_templatetags.py.

    # https://creativecommons.org/licenses/by-sa/4.0/
    # https://creativecommons.org/licenses/by-sa/4.0/deed.es
    # https://creativecommons.org/licenses/by/3.0/es/
    # https://creativecommons.org/licenses/by/3.0/es/deed.fr

    if jurisdiction_code:
        if language_code == "en" or not language_code:
            return f"/licenses/{license_code}/{version}/{jurisdiction_code}/"
        else:
            return f"/licenses/{license_code}/{version}/{jurisdiction_code}/deed.{language_code}"
    else:
        if language_code == "en" or not language_code:
            return f"/licenses/{license_code}/{version}/"
        else:
            return f"/licenses/{license_code}/{version}/deed.{language_code}"
