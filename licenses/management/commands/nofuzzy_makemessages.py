# Third-party
from django.core.management.commands import makemessages

class Command(makemessages.Command):
    # For Django default msgmerge options, see:
    # https://github.com/django/django/blob/stable/3.2.x/django/core/management/commands/makemessages.py#L211
    # As of 2021-10-22, the defaults are:
    # msgmerge_options = ['-q', '--previous']
    msgmerge_options = ["--no-fuzzy-matching", "--previous", "--quiet"]
