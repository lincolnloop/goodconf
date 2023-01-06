import re
from textwrap import dedent
from typing import Optional

import pytest
from pydantic import Field, ValidationError

from goodconf import GoodConf


def test_initial():
    class TestConf(GoodConf):
        a: bool = Field(initial=lambda: True)
        b: bool = Field(default=False)

    initial = TestConf.get_initial()
    assert len(initial) == 2
    assert initial["a"] is True
    assert initial["b"] is False


def test_dump_json():
    class TestConf(GoodConf):
        a: bool = Field(initial=lambda: True)

    assert TestConf.generate_json() == '{\n  "a": true\n}'
    assert TestConf.generate_json(not_a_value=True) == '{\n  "a": true\n}'
    assert TestConf.generate_json(a=False) == '{\n  "a": false\n}'


def test_dump_toml():
    pytest.importorskip("tomlkit")

    class TestConf(GoodConf):
        a: bool = False
        b: str = "Happy"

    output = TestConf.generate_toml()
    assert "a = false" in output
    assert 'b = "Happy"' in output

    class TestConf(GoodConf):
        "Configuration for My App"
        a: str = Field(description="this is a")
        b: str

    output = TestConf.generate_toml()

    assert "# Configuration for My App\n" in output
    assert 'a = "" # this is a' in output
    assert 'b = ""' in output


def test_dump_yaml():
    pytest.importorskip("ruamel.yaml")

    class TestConf(GoodConf):
        "Configuration for My App"
        a: str = Field(description="this is a")
        b: str

    output = TestConf.generate_yaml()
    output = re.sub(r" +\n", "\n", output)
    assert "\n# Configuration for My App\n" in output
    assert (
        dedent(
            """\
        # this is a
        a: ''
        """
        )
        in output
    )
    assert "b: ''" in output

    output_override = TestConf.generate_yaml(b="yes")
    assert "a: ''" in output_override
    assert "b: yes" in output_override


def test_dump_yaml_no_docstring():
    pytest.importorskip("ruamel.yaml")

    class TestConf(GoodConf):
        a: str = Field(description="this is a")

    output = TestConf.generate_yaml()
    output = re.sub(r" +\n", "\n", output)
    assert output == dedent(
        """
        # this is a
        a: ''
        """
    )


def test_dump_yaml_none():
    pytest.importorskip("ruamel.yaml")

    class TestConf(GoodConf):
        a: Optional[str]

    output = TestConf.generate_yaml()
    assert output.strip() == "a: ~"


def test_generate_markdown():
    help_ = "this is a"

    class TestConf(GoodConf):
        "Configuration for My App"
        a: int = Field(description=help_, default=5)
        b: str

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert TestConf.__doc__ in mkdn
    assert help_ in mkdn


def test_generate_markdown_no_docsttring():
    help_ = "this is a"

    class TestConf(GoodConf):
        a: int = Field(description=help_, default=5)
        b: str

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert help_ in mkdn


def test_generate_markdown_default_false():
    class TestConf(GoodConf):
        a: bool = Field(default=False)

    assert "False" in TestConf.generate_markdown()


def test_undefined():
    c = GoodConf()
    with pytest.raises(AttributeError):
        c.UNDEFINED


def test_required_missing():
    class TestConf(GoodConf):
        a: str = Field()

    c = TestConf()

    with pytest.raises(ValidationError):
        c.load()

    with pytest.raises(ValidationError):
        TestConf(load=True)
