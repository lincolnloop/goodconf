import re
from textwrap import dedent

import pytest
from pydantic import ValidationError

from goodconf import GoodConf
from goodconf.values import Value


def test_initial():
    class TestConf(GoodConf):
        a: bool = Value(initial=lambda: True)
        b: bool = Value(default=False)

    initial = TestConf.get_initial()
    assert len(initial) == 2
    assert initial["a"] is True
    assert initial["b"] is False


def test_dump_json():
    class TestConf(GoodConf):
        a: bool = Value(initial=lambda: True)

    assert TestConf.generate_json() == '{\n  "a": true\n}'
    assert TestConf.generate_json(not_a_value=True) == '{\n  "a": true\n}'
    assert TestConf.generate_json(a=False) == '{\n  "a": false\n}'


def test_dump_yaml():
    pytest.importorskip("ruamel.yaml")

    class TestConf(GoodConf):
        "Configuration for My App"
        a: str = Value(description="this is a")
        b: str

    output = TestConf.generate_yaml()
    output = re.sub(r" +\n", "\n", output)
    assert (
        dedent(
            """\
        #
        # Configuration for My App
        #
        """
        )
        in output
    )
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
        a: str = Value(description="this is a")

    output = TestConf.generate_yaml()
    output = re.sub(r" +\n", "\n", output)
    assert output == dedent(
        """
        # this is a
        a: ''
        """
    )


def test_generate_markdown():
    help_ = "this is a"

    class TestConf(GoodConf):
        "Configuration for My App"
        a: int = Value(description=help_, default=5)
        b: str

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert TestConf.__doc__ in mkdn
    assert help_ in mkdn


def test_generate_markdown_no_docsttring():
    help_ = "this is a"

    class TestConf(GoodConf):
        a: int = Value(description=help_, default=5)
        b: str

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert help_ in mkdn


def test_generate_markdown_default_false():
    class TestConf(GoodConf):
        a: bool = Value(default=False)

    assert "False" in TestConf.generate_markdown()


def test_undefined():
    c = GoodConf()
    with pytest.raises(AttributeError):
        c.UNDEFINED


def test_required_missing():
    class TestConf(GoodConf):
        a: str = Value()

    c = TestConf()

    with pytest.raises(ValidationError):
        c.load()

    with pytest.raises(ValidationError):
        TestConf(load=True)
