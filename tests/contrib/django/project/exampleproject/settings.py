from tests.contrib.django.project.exampleproject.conf import config

config.load()

SECRET_KEY = "goodconf-tests"
INSTALLED_APPS: list[str] = []
APP_NAME = config.APP_NAME
