# Third-party
from django.core.management.commands import makemessages


class Command(makemessages.Command):
    # For Django 4.2 default msgmerge options, see:
    # https://github.com/django/django/blob/stable/4.2.x/django/core/management/commands/makemessages.py#L222
    # As of 2025-02-10, the defaults are:
    # msgmerge_options = ["-q", "--backup=none", "--previous", "--update"]
    #
    # override options:
    msgmerge_options = [
        "--backup=none",
        "--no-fuzzy-matching",
        "--previous",
        "--quiet",
        "--update",
    ]
