# Creative Commons Licenses Infrastructure

### Getting Started

`make setup`

This command will:
1. Create a virtual environment called **cc-licenses**, install python, and python dependencies
2. Create a Postgres Database called **cc_licenses** and run database migrations

Please see **Makefile** in the root directory for a closer look at the commands we are running.

After installation is complete. Run:

1. `workon cc-licenses`
2. `cd cc_licenses && python manage.py runserver`
