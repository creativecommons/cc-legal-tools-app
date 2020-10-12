# language identifiers that currently are not supported by python-babel.
# see i18n.utils, Locale.parse()
EXCLUDED_LANGUAGE_IDENTIFIERS = ["nso", "oci-es", "x-i18n", "st"]
# Exclude non 4.0 licenses for right now
EXCLUDED_LICENSE_VERSIONS = ["3.0", "2.5", "2.1", "2.0", ""]
# All Versions
LICENSE_VERSIONS = EXCLUDED_LICENSE_VERSIONS + ["1.0", "4.0"]
