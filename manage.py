# Generally, it is best to avoid calling this file directly. Examples in order
# from best to worst:
#   ./bin/manage.sh -h
#   docker compose exec app python ./manage.py -h
#   pipenv run python manage.py -h

# Standard library
import logging
import sys

# Third-party
from django.core.management import execute_from_command_line

LOG = logging.getLogger("management.commands")


def main():
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
