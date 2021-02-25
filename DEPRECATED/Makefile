# This makefile assumes you're activated your virtual environment first.
PROJECT_NAME = cc_licenses
STATIC_DIR = ./$(PROJECT_NAME)/static

# note: the pre-commit hooks do both linting and testing.
test:
	# Run all tests and report coverage
	pre-commit run -v -a

# Generate a random string of desired length
generate-secret: length = 32
generate-secret:
	@strings /dev/urandom | grep -o '[[:alnum:]]' | head -n $(length) | tr -d '\n'; echo

conf/keys/%.pub.ssh:
	# Generate SSH deploy key for a given environment
	ssh-keygen -t rsa -b 4096 -f $*.priv -C "$*@${PROJECT_NAME}"
	@mv $*.priv.pub $@

staging-deploy-key: conf/keys/staging.pub.ssh

production-deploy-key: conf/keys/production.pub.ssh

# Translation helpers
makemessages:
	# Extract English messages from our source code
	python manage.py makemessages

compile_messages:
	# Compile PO files into the MO files that Django will use at runtime
	python manage.py compilemessages

pushmessages:
	# Upload the latest English PO file to Transifex
	tx push -s

pullmessages:
	# Pull the latest translated PO files from Transifex
	tx pull -af

setup:
	if [ "${VIRTUAL_ENV}" = "" ] ; then echo "Please create and activate a python 3.7 virtual environment, then try again"; false; fi
	pip install -U pip wheel
	pip install -Ur requirements/dev.txt
	pip freeze
	cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
	echo "DJANGO_SETTINGS_MODULE=cc_licenses.settings.local" > .env
	createdb -E UTF-8 cc_licenses
	python manage.py migrate
	if [ -e project.travis.yml ] ; then mv project.travis.yml .travis.yml; fi
	@echo
	@echo "The cc_licenses project is now setup on your machine."
	@echo "Run the following commands to activate the virtual environment and run the"
	@echo "development server:"
	@echo
	@echo "	workon cc_licenses"
	@echo "	python manage.py runserver"

update:
	pip install -U -r requirements/dev.txt

# Build documentation
docs:
	cd docs && make html

.PHONY: default test lint lint-py lint-js generate-secret makemessages \
		pushmessages pullmessages compilemessages docs

.PRECIOUS: conf/keys/%.pub.ssh
