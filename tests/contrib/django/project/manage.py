import os

from tests.contrib.django.project.conf import config

if __name__ == "__main__":
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "tests.contrib.django.project.settings"
    )
    config.django_manage()
