#!/usr/bin/env python
# Standard library
import logging
import os
import sys

LOG = logging.getLogger("management.commands")


def main():
    if "DATABASE_URL" in os.environ:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "cc_legal_tools.settings.deploy"
        )
    else:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "cc_legal_tools.settings.local"
        )

    # Third-party
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except KeyboardInterrupt:
        LOG.info("Halted via KeyboardInterrupt.")
        sys.exit(130)
    except Exception:
        LOG.exception("Unhandled exception:")
        sys.exit(1)
