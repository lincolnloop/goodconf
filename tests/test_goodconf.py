import re
from textwrap import dedent

import pytest
from goodconf import GoodConf
from goodconf.values import Value, RequiredValueMissing


def test_define_values():

    class MyConf(GoodConf):
        a = Value()
        c = Value()
        b = Value()

    v = MyConf._values
    assert list(v.keys()) == ['a', 'c', 'b'], "Order should be retained"

    assert v['a'].key == 'a', "Keys are implicitly set"
    assert v['b'].key == 'b', "Keys are implicitly set"


def test_explicit_key():

    with pytest.raises(AttributeError):

        class BadConf(GoodConf):
            a = Value(key='not_a')


def test_defaults():

    class MyConf(GoodConf):
        a = Value()
        b = Value(default='fish')

    conf = MyConf()

    assert conf.a is None
    assert conf.b == 'fish'


def test_set_values():

    class TestConf(GoodConf):
        a = Value(default='')
        c = Value(default=4)

    c = TestConf()
    c.set_values({'a': 'b'})
    assert c.a == 'b'
    assert c.c == 4


def test_set_values_again():

    class TestConf(GoodConf):
        a = Value(default='')
        c = Value(default=4)

    c = TestConf()
    c.set_values({'a': 'b'})
    c.set_values({'c': 1})
    assert c.a == ''
    assert c.c == 1


def test_initial():

    class TestConf(GoodConf):
        a = Value(initial=lambda: True)
        b = Value(default=False)

    initial = TestConf.get_initial()
    assert len(initial) == 2
    assert initial['a'] is True
    assert initial['b'] is False


def test_dump_json():

    class TestConf(GoodConf):
        a = Value(initial=lambda: True)

    assert TestConf.generate_json() == '{\n  "a": true\n}'
    assert TestConf.generate_json(not_a_value=True) == '{\n  "a": true\n}'
    assert TestConf.generate_json(a=False) == '{\n  "a": false\n}'


def test_dump_yaml():
    pytest.importorskip('ruamel.yaml')

    class TestConf(GoodConf):
        "Configuration for My App"
        a = Value(help="this is a")
        b = Value()

    output = TestConf.generate_yaml()
    output = re.sub(r' +\n', '\n', output)
    assert dedent("""\
        #
        # Configuration for My App
        #
        """) in output
    assert dedent("""\
        # this is a
        a: ''
        """) in output
    assert "b: ''" in output

    output_override = TestConf.generate_yaml(b='yes')
    assert "a: ''" in output_override
    assert "b: yes" in output_override


def test_dump_yaml_no_docstring():
    pytest.importorskip('ruamel.yaml')

    class TestConf(GoodConf):
        a = Value(help="this is a")

    output = TestConf.generate_yaml()
    output = re.sub(r' +\n', '\n', output)
    assert output == dedent("""
        # this is a
        a: ''
        """)


def test_generate_markdown():
    help_ = "this is a"

    class TestConf(GoodConf):
        "Configuration for My App"
        a = Value(help=help_, default=5)
        b = Value()

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert TestConf.__doc__ in mkdn
    assert help_ in mkdn


def test_generate_markdown_no_docsttring():
    help_ = "this is a"

    class TestConf(GoodConf):
        a = Value(help=help_, default=5)
        b = Value()

    mkdn = TestConf.generate_markdown()
    # Not sure on final format, just do some basic smoke tests
    assert help_ in mkdn


def test_undefined():
    c = GoodConf()
    with pytest.raises(AttributeError):
        c.UNDEFINED


def test_required_missing():

    class TestConf(GoodConf):
        a = Value()

    c = TestConf()

    with pytest.raises(RequiredValueMissing):
        c.load()

    with pytest.raises(RequiredValueMissing):
        TestConf(load=True)


def test_nested():

    class ParentConf(GoodConf):
        a = Value()

    class ChildConf(ParentConf):
        b = Value()

    assert list(ChildConf._values.keys()) == ['b', 'a']
