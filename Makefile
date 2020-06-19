PROJECT_NAME = cc-licenses
PROJECT_DIR = cc_licenses
STATIC_DIR = ./$(PROJECT_NAME)/static

setup:
	virtualenv -p `which python3.7` $(WORKON_HOME)/$(PROJECT_NAME)
	$(WORKON_HOME)/$(PROJECT_NAME)/bin/pip install -U pip wheel
	$(WORKON_HOME)/$(PROJECT_NAME)/bin/pip install -Ur requirements/dev.txt
	$(WORKON_HOME)/$(PROJECT_NAME)/bin/pip freeze
	createdb -E UTF-8 $(PROJECT_DIR)
	cd cc_licenses && $(WORKON_HOME)/$(PROJECT_NAME)/bin/python manage.py migrate
	@echo
	@echo "The cc-licenses project is now setup on your machine."
	@echo "Run the following commands to activate the virtual environment and run the"
	@echo "development server:"
	@echo
	@echo "	workon cc-licenses"
	@echo " cd cc_licenses && python manage.py runserver"

update:
	$(WORKON_HOME)/$(PROJECT_NAME)/bin/pip install -U -r requirements/dev.txt
