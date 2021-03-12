import pytest

from goodconf import GoodConf, Field, initial_for_field

from .utils import KEY


def test_initial():
    f = Field(initial=lambda: "x")
    assert initial_for_field(KEY, f) == "x"


def test_initial_bad():
    f = Field(initial="x")
    with pytest.raises(ValueError):
        initial_for_field(KEY, f)


def test_initial_default():
    f = Field("x")
    assert initial_for_field(KEY, f) == "x"


def test_initial_default_factory():
    f = Field(default_factory=lambda: "y")
    assert initial_for_field(KEY, f) == "y"


def test_no_initial():
    f = Field()
    assert initial_for_field(KEY, f) == ""


def test_default_initial():
    """Can get initial when Field is not used"""

    class G(GoodConf):
        a: str = "test"

    initial = G().get_initial()
    assert initial["a"] == "test"
