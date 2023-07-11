#!/usr/bin/env python3

"""
Display Babel / CLDR locale data for a given language tag
"""

# Standard library
import argparse
import sys
import traceback

# Third-party
from babel import Locale
from django.utils import translation


class ReportError(Exception):
    def __init__(self, message, code=None):
        self.code = code if code else 1
        message = f"({self.code}) {message}"
        super(ReportError, self).__init__(message)


def setup():
    """Instantiate and configure argparse and logging.

    Return argsparse namespace.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("language_tag", metavar="LANUAGE_TAG")
    args = ap.parse_args()
    args.language_tag = args.language_tag.lower()
    return args


def main():
    args = setup()
    locale_name = translation.to_locale(args.language_tag)
    locale = Locale.parse(locale_name)
    name = locale.get_display_name("en")
    name_local = locale.get_display_name(locale_name)
    character_order = locale.character_order
    print()
    print(
        f"      LANUAGE_TAG: {args.language_tag}",
        "",
        "Django",
        f"           locale: {locale_name}",
        "",
        "Babel / CLDR",
        f"           locale: {locale}",
        f"             name: {name}",
        f"       name_local: {name_local}",
        f"  character_order: {character_order}",
        sep="\n",
    )
    print()


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except KeyboardInterrupt:
        print("INFO (130) Halted via KeyboardInterrupt.", file=sys.stderr)
        sys.exit(130)
    except ReportError:
        error_type, error_value, error_traceback = sys.exc_info()
        print(f"CRITICAL {error_value}", file=sys.stderr)
        sys.exit(error_value.code)
    except Exception:
        print("ERROR (1) Unhandled exception:", file=sys.stderr)
        print(traceback.print_exc(), file=sys.stderr)
        sys.exit(1)
