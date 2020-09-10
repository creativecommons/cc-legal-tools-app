from django import template

register = template.Library()


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
