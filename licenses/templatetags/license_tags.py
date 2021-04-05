# Standard library
import string
from threading import local

# Third-party
from django import template

register = template.Library()


# This is kind of gross, but it lets us simply produce
# a stream of letters and insert them into our template, without
# needing a for-loop or anything.

# Store state here. Use a thread-local so at least this is thread-safe.
next_letter_data = local()


@register.filter
def license_codes(legalcodes):
    """
    Return sorted list of the unique license codes for the given
    dictionaries representing legalcodes
    """
    return sorted(set(lc["license_code"] for lc in legalcodes))


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
        raise ValueError(
            "Arg to reset_letters should be 'lowercase' or 'uppercase'"
        )
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
