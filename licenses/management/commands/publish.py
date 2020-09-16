import subprocess
from argparse import ArgumentParser

from django.core.management import BaseCommand
from cc_licenses.settings.base import TRANSLATION_REPOSITORY_DIRECTORY

# Go to cc-licenses-data and do something
GO_TO_TRANSLATIONS_REPO = f"cd {TRANSLATION_REPOSITORY_DIRECTORY} && "
UPDATE_CMD = "git checkout develop && git pull"
PULL_DOWN_TRANSLATION_BRANCHES = GO_TO_TRANSLATIONS_REPO + UPDATE_CMD

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

def list_open_branches():
    """List of open branches in cc-licenses-data repo
    """
    list_branches_cmd = GO_TO_TRANSLATIONS_REPO + "git branch"
    print("\nBranch name to publish artifacts to must be supplied.\n")
    pull_translations_branches()
    branches = subprocess.check_output(list_branches_cmd, shell=True).decode().split('\n')
    branches = list(branches)
    print("\nActive cc-licenses-data branches:\n")
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
            list_open_branches()

