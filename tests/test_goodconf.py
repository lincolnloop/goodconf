import json
import os
import re
from textwrap import dedent
from typing import Optional, List, Literal

import pytest
from pydantic import BaseModel, Field, ValidationError

from goodconf import GoodConf
from tests.utils import env_var


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


def test_dump_complex_toml():
    """Dump a complex configuration class, with inner classes and lists"""
    pytest.importorskip("tomlkit")
    import tomlkit

    class TestConf(GoodConf):
        class A(BaseModel):
            inner: bool = False
            index: int

        outer = A(index=0)
        simple_list: list[int] = [1, 2]
        complex_list: list[A] = [A(index=0)]

    output = TestConf.generate_toml()
    assert "[outer]" in output
    assert "inner = false" in output

    # Check that generated toml is valid
    doc = tomlkit.parse(output)
    assert doc["outer"]["inner"] is False

    # Check the lists
    assert len(doc["simple_list"]) == 2
    assert doc["simple_list"][0] == 1
    assert doc["complex_list"][0]["index"] == 0


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


def test_generate_markdown_no_docstring():
    help_ = "this is a"

    class TestConf(GoodConf):
        a: int = Field(description=help_, default=5)
        b: str

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert f"  * description: {help_}" in mkdn.splitlines()


def test_generate_markdown_default_false():
    class TestConf(GoodConf):
        a: bool = Field(default=False)

    lines = TestConf.generate_markdown().splitlines()
    assert "  * type: `bool`" in lines
    assert "  * default: `False`" in lines


def test_generate_markdown_types():
    class TestConf(GoodConf):
        a: Literal["a", "b"] = Field(default="a")
        b: List[str] = Field()

    lines = TestConf.generate_markdown().splitlines()
    assert "  * type: `Literal['a', 'b']`" in lines
    assert "  * type: `list[str]`" in lines


def test_generate_markdown_required():
    class TestConf(GoodConf):
        a: str

    lines = TestConf.generate_markdown().splitlines()
    assert "* **a** _REQUIRED_" in lines


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


def test_set_on_init():
    class TestConf(GoodConf):
        a: str = Field()

    val = "test"
    c = TestConf(a=val)
    assert c.a == val


def test_env_prefix():
    class TestConf(GoodConf):
        a: bool = False

        class Config:
            env_prefix = "PREFIX_"

    with env_var("PREFIX_A", "True"):
        c = TestConf(load=True)

    assert c.a


def test_precedence(tmpdir):
    path = tmpdir.join("myapp.json")
    path.write(json.dumps({"init": "file", "env": "file", "file": "file"}))

    class TestConf(GoodConf, default_files=[path]):
        init: str = ""
        env: str = ""
        file: str = ""

    os.environ["INIT"] = "env"
    os.environ["ENV"] = "env"
    try:
        c = TestConf(init="init")
        assert c.init == "init"
        assert c.env == "env"
        assert c.file == "file"
    finally:
        del os.environ["INIT"]
        del os.environ["ENV"]
