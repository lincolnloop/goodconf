import pytest

from goodconf import GoodConf
from goodconf.values import Value
from .utils import KEY


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


def test_both_defaults():
    with pytest.raises(ValueError):
        Value(KEY, default=True, default_factory=lambda: False)


def test_default_initial():
    """Can get initial when Value is not used"""
    class G(GoodConf):
        a: str = "test"
    initial = G().get_initial()
    assert initial["a"] == "test"
