import pytest
from django.core.management.base import BaseCommand

from goodconf import GoodConf, GoodConfConfigDict
from goodconf.contrib.django import load_config_from_cli


@pytest.mark.legacy
def test_create_parser_forwards_kwargs() -> None:
    class G(GoodConf):
        model_config = GoodConfConfigDict()

    with load_config_from_cli(G(), ["manage.py"]):
        parser = BaseCommand().create_parser("manage.py", "check", usage="custom usage")

    assert parser.format_usage() == "usage: custom usage\n"
