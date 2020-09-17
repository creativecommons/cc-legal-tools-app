import os
import subprocess
import datetime
from argparse import ArgumentParser

from django.core.management import BaseCommand
from cc_licenses.settings.base import TRANSLATION_REPOSITORY_DIRECTORY

# Go to cc-licenses-data and do something
GO_TO_TRANSLATIONS_REPO = f"cd {TRANSLATION_REPOSITORY_DIRECTORY} && "
PULL_BRANCHES_DOWN_FROM_DEVELOP = "git checkout develop && git pull"
PULL_DOWN_TRANSLATION_BRANCHES = GO_TO_TRANSLATIONS_REPO + PULL_BRANCHES_DOWN_FROM_DEVELOP

def run_django_distill():
    """Outputs the build directory
    """
    my_env = os.environ.copy()
    my_env["DJANGO_SETTINGS_MODULE"] = "cc_licenses.settings.publish"
    cmd = 'python manage.py distill-local --quiet --force'
    return subprocess.run(
      cmd,
      shell=True,
      check=True,
      text=True,
      input="YES",
      env=my_env,
    )

def git_branch_status(branch: str):
    """Checks if there is a build to commit using git status

    Returns True or False
    """
    check_branch_status_cmd = GO_TO_TRANSLATIONS_REPO + f"git checkout {branch} && " + "git status"
    status = subprocess.check_output(check_branch_status_cmd, shell=True).decode().split('\n')
    if 'nothing to commit, working tree clean' in status:
        return False
    return True

def git_on_branch_and_pull(branch: str):
    """Returns a string represention of the git command to checkout and pull from a branch"""
    git_on_branch_and_pull_cmd = GO_TO_TRANSLATIONS_REPO + (
      f"git checkout {branch} && git pull origin {branch}"
    )
    return subprocess.run(
      git_on_branch_and_pull_cmd,
      shell=True,
      check=True
    )


def git_commit_and_push(branch: str):
  """Returns a string representation of the git command to checkout, commit, and push branch"""
  commit_and_push_cmd = GO_TO_TRANSLATIONS_REPO + (
      "git add build/ && "
      f"git checkout {branch} && "
      f"git commit -m '{branch} ' && " 
      f"git push origin {branch}"
  )
  return subprocess.run(
    commit_and_push_cmd,
    shell=True,
    check=True,
  )

def pull_translations_branches():
    """Git pulls branches in cc-licenses-data to update local git registry"""
    return subprocess.run(
        PULL_DOWN_TRANSLATION_BRANCHES,
        shell=True,
        check=True,
      )

def list_open_branches():
    """List of open branches in cc-licenses-data repo
    """
    list_branches_cmd = GO_TO_TRANSLATIONS_REPO + "git branch --list"
    pull_translations_branches()
    branches = subprocess.check_output(list_branches_cmd, shell=True).decode().split('\n')
    print("\n\nWhich branch are we publishing to?\n")
    [print(b) for b in branches]


def publish_branch(branch: str):
    """Workflow for publishing a single branch"""
    git_on_branch_and_pull(branch)
    run_django_distill()
    build_to_push = git_branch_status(branch)
    if build_to_push:
        git_commit_and_push(branch)
    else:
        print(f"\n{branch} build dir is up to date.\n")

def publish_all():
    """Workflow for checking branches other than develop and updating their build dir
    
    Develop is not checked because it serves as the source of truth. It should be
    manually merged into.
    """
    list_branches_cmd = GO_TO_TRANSLATIONS_REPO + "git branch --list"
    branches = subprocess.check_output(list_branches_cmd, shell=True).decode().split('\n')
    exclude_develop_list = [b for b in branches if 'develop' not in b]
    del exclude_develop_list[-1]
    branch_list = [b.lstrip() for b in exclude_develop_list]
    print(f"\n\nChecking and updating build dirs for {len(branch_list)} translation branches")
    [publish_branch(b) for b in branch_list]
    

class Command(BaseCommand):
    """Command to push the static files in the build directory to a specified branch 
    in cc-licenses-data repository

    Arguments:
        branch_name - Branch name in cc-license-data to pull translations from 
                      and publish artifacts too.
        list_branches - A list of active branches in cc-licenses-data will be
                        displayed

    If no arguments are supplied all cc-licenses-data branches are checked and
    then updated.
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
        parser.add_argument(
          "-l",
          "--list_branches",
          action="store_true",
          help="A list of active branches in cc-licenses-data will be displayed"
        )

    def handle(self, *args, **options):
        if options.get("list_branches"):
            return list_open_branches()
        if options.get("branch_name"):
            return publish_branch(options["branch_name"])
        return publish_all()
