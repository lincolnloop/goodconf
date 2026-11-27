import sys

import django
from django.conf import settings


def print_app_name() -> None:
    django.setup()
    sys.stdout.write(f"{settings.APP_NAME}\n")
    sys.stdout.flush()
