# language identifiers that currently are not supported by python-babel.
# see i18n.utils, Locale.parse()
EXCLUDED_LANGUAGE_IDENTIFIERS = ["nso", "oci-es", "x-i18n", "st"]
# NOTE that "CC0" is technically a 1.0 license and we are including that, but
# no other "1.0" licenses yet. We just won't create any other "1.0" License or
# LegalCode objects until we're ready for the other "1.0" licenses.
# This list is the versions we are *completely* excluding.
EXCLUDED_LICENSE_VERSIONS = ["3.0", "2.5", "2.1", "2.0"]
INCLUDED_LICENSE_VERSIONS = ["4.0", "1.0"]
# All Versions
LICENSE_VERSIONS = EXCLUDED_LICENSE_VERSIONS + INCLUDED_LICENSE_VERSIONS
