import subprocess
from argparse import ArgumentParser

from django.core.management import BaseCommand
from cc_licenses.settings.base import TRANSLATION_REPOSITORY_DIRECTORY

# Go to cc-licenses-data and do something
GO_TO_TRANSLATIONS_REPO = f"cd {TRANSLATION_REPOSITORY_DIRECTORY} && "
PULL_BRANCHES_DOWN_FROM_DEVELOP = "git checkout develop && git pull"
PULL_DOWN_TRANSLATION_BRANCHES = GO_TO_TRANSLATIONS_REPO + PULL_BRANCHES_DOWN_FROM_DEVELOP

def set_publish_settings():
    """Set environment to use publish settings
    
    This is so when django-distill runs it places
    the build directory in the cc-licenses-data repo
    """
    set_env_settings = (
        "unset DJANGO_SETTINGS_MODULE && "
        "export DJANGO_SETTINGS_MODULE=cc_licenses.settings.publish"
    )
    return subprocess.run(
        set_env_settings,
        shell=True,
        check=True,
    )

def set_default_settings():
    """Set environment to use the default settings
    
    Cleanup definition: When django-distill finishes we should have 
    the build directory outputting to the cc-licenses directory for
    development purposes.
    """
    set_env_settings = (
        "unset DJANGO_SETTINGS_MODULE && "
        "export DJANGO_SETTINGS_MODULE=cc_licenses.settings.dev"
    )
    return subprocess.run(
        set_env_settings,
        shell=True,
        check=True,
    )

def run_django_distill():
    """Outputs the build directory
    """
    return subprocess.run(
      'python manage.py distill-local --quiet --force'
    )

def pull_translations_branches():
    """Git pulls branches in cc-licenses-data to update local git registry"""
    return subprocess.run(
        PULL_DOWN_TRANSLATION_BRANCHES,
        shell=True,
        check=True,
      )

def git_on_branch_and_pull_str(branch: str) -> str:
    """Returns a string represention of the git command to checkout and pull from a branch"""
    return f"git checkout {branch} && git pull origin {branch}"

def git_commit_and_push(branch: str) --> str:
  """Returns a string representation of the git command to checkout, commit, and push branch"""
    return f"git checkout {branch} && git push origin {branch}"

def list_open_branches():
    """List of open branches in cc-licenses-data repo
    """
    list_branches_cmd = GO_TO_TRANSLATIONS_REPO + "git branch --list"
    print(
      "\n'branch_name' to publish artifacts to must be supplied.\n"
      "Retrieving active branches from cc-licenses-data...\n\n"
    )
    pull_translations_branches()
    branches = subprocess.check_output(list_branches_cmd, shell=True).decode().split('\n')
    print("\n\nWhich branch are we publishing to?\n")
    [print(b) for b in branches]

    


class Command(BaseCommand):
    """Command to push the static files in the build directory to a specified branch 
    in cc-licenses-data repository

    Arguments:
        branch_name - Branch name in cc-license-data to pull translations from 
                      and publish artifacts too. If not specified a list of 
                      active branches in cc-licenses-data will be displayed.
    """

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument(
          "-b",
          "--branch_name",
          help=(
              "Branch name in cc-license-data to pull translations from "
              "and push artifacts too. If not specified a list of active "
              "branches in cc-licenses-data will be displayed"
          )
        )
    def handle(self, *args, **options):
        if not options.get("branch_name"):
            return list_open_branches()
        branch_cmd = git_on_branch_and_pull_str(options["branch_name"])
        print(branch_cmd)
