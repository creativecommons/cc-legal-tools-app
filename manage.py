#!/usr/bin/env python
# Standard library
import os
import sys
import traceback


class ScriptError(Exception):
    def __init__(self, message, code=None):
        self.code = code if code else 1
        message = "({}) {}".format(self.code, message)
        super(ScriptError, self).__init__(message)


def main():
    if "DATABASE_URL" in os.environ:
        # Dokku or similar
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "cc_licenses.settings.deploy"
        )
    else:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE", "cc_licenses.settings.local"
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
        print("INFO (130) Halted via KeyboardInterrupt.", file=sys.stderr)
        sys.exit(130)
    except ScriptError:
        error_type, error_value, error_traceback = sys.exc_info()
        print("CRITICAL {}".format(error_value), file=sys.stderr)
        sys.exit(error_value.code)
    except Exception:
        print("ERROR (1) Unhandled exception:", file=sys.stderr)
        print(traceback.print_exc(), file=sys.stderr)
        sys.exit(1)
