PROJECT_NAME = cc_licenses
STATIC_DIR = ./$(PROJECT_NAME)/static
WORKON_HOME ?= $(HOME)/.virtualenvs
VENV_DIR ?= $(WORKON_HOME)/$(PROJECT_NAME)

default: lint test

test:
	# Run all tests and report coverage
	# Requires coverage
	python manage.py makemigrations --dry-run | grep 'No changes detected' || \
		(echo 'There are changes which require migrations.' && exit 1)
	coverage run manage.py test --noinput
	coverage report -m --fail-under 80
	npm test

lint-py:
	# Check for Python formatting issues
	# Requires flake8
	$(VENV_DIR)/bin/flake8 .

lint-js:
	# Check JS for any problems
	# Requires jshint
	./node_modules/.bin/eslint -c .eslintrc '${STATIC_DIR}' --ext js,jsx

lint: lint-py lint-js

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
	python manage.py makemessages --ignore 'conf/*' --ignore 'docs/*' --ignore 'requirements/*' \
		--no-location --no-obsolete -l en

compilemessages:
	# Compile PO files into the MO files that Django will use at runtime
	python manage.py compilemessages

pushmessages:
	# Upload the latest English PO file to Transifex
	tx push -s

pullmessages:
	# Pull the latest translated PO files from Transifex
	tx pull -af

setup:
	virtualenv -p `which python3.8` $(VENV_DIR)
	$(VENV_DIR)/bin/pip install -U pip wheel
	$(VENV_DIR)/bin/pip install -Ur requirements/dev.txt
	$(VENV_DIR)/bin/pip freeze
	npm install
	npm update
	cp cc_licenses/settings/local.example.py cc_licenses/settings/local.py
	echo "DJANGO_SETTINGS_MODULE=cc_licenses.settings.local" > .env
	createdb -E UTF-8 cc_licenses
	$(VENV_DIR)/bin/python manage.py migrate
	if [ -e project.travis.yml ] ; then mv project.travis.yml .travis.yml; fi
	@echo
	@echo "The cc_licenses project is now setup on your machine."
	@echo "Run the following commands to activate the virtual environment and run the"
	@echo "development server:"
	@echo
	@echo "	workon cc_licenses"
	@echo "	npm run dev"

update:
	$(VENV_DIR)/bin/pip install -U -r requirements/dev.txt
	npm install
	npm update

# Build documentation
docs:
	cd docs && make html

.PHONY: default test lint lint-py lint-js generate-secret makemessages \
		pushmessages pullmessages compilemessages docs

.PRECIOUS: conf/keys/%.pub.ssh
