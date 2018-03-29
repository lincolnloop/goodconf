import pytest
from goodconf.values import Value, RequiredValueMissing
from .utils import KEY, env_var


def test_default_not_required():
    """Values with a default are not required"""
    v = Value(KEY, default='s')
    assert v.required is False


def test_no_default_required():
    """Values with a default are not required"""
    v = Value(KEY)
    assert v.required is True


def test_infer_cast():
    """If not provided, cast is type of default"""
    v = Value(KEY, default=5)
    assert v.cast_as == int


def test_default_cast():
    """Default cast is str"""
    v = Value(KEY)
    assert v.cast_as == str


def test_default_callable():
    v = Value(KEY, default=lambda: 's')
    assert v.value == 's'


def test_explicit_cast():
    v = Value(KEY, cast_as=bool)
    assert v.cast_as == bool


def test_cast_bool():
    v = Value(KEY, cast_as=bool)
    with env_var(KEY, 'true'):
        assert v.value is True
    with env_var(KEY, 'false'):
        assert v.value is False


def test_initial():
    v = Value(KEY, initial=lambda: 'x')
    assert v.initial == 'x'


def test_initial_bad():
    with pytest.raises(ValueError):
        Value(KEY, initial='x')


def test_initial_default():
    v = Value(KEY, default='x')
    assert v.initial == 'x'


def test_no_initial():
    v = Value(KEY)
    assert v.initial == ''


def test_defined_value():
    v = Value(KEY)
    v.value = 'x'
    assert v.value == 'x'


def test_env_var_precedence():
    v = Value(KEY)
    with env_var(KEY, 'y'):
        v.value = 'x'
        assert v.value == 'y'


def test_required_no_value():
    v = Value(KEY)
    with pytest.raises(RequiredValueMissing):
        v.value = None


def test_cast_list():
    v = Value(KEY, cast_as=list)
    with env_var(KEY, 'a,b,c'):
        assert v.value == ['a', 'b', 'c']
