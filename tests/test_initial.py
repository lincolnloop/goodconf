from typing import Optional

import pytest

from goodconf import GoodConf, Field, initial_for_field

from .utils import KEY


def test_initial():
    class C(GoodConf):
        f = Field(initial=lambda: "x")

    assert initial_for_field(KEY, C.__fields__["f"]) == "x"


def test_initial_bad():
    class C(GoodConf):
        f = Field(initial="x")

    with pytest.raises(ValueError):
        initial_for_field(KEY, C.__fields__["f"])


def test_initial_default():
    class C(GoodConf):
        f = Field("x")

    assert initial_for_field(KEY, C.__fields__["f"]) == "x"


def test_initial_default_factory():
    class C(GoodConf):
        f: str = Field(default_factory=lambda: "y")

    assert initial_for_field(KEY, C.__fields__["f"]) == "y"


def test_no_initial():
    class C(GoodConf):
        f = Field()

    assert initial_for_field(KEY, C.__fields__["f"]) == ""


def test_default_initial():
    """Can get initial when Field is not used"""

    class G(GoodConf):
        a: str = "test"

    initial = G().get_initial()
    assert initial["a"] == "test"


def test_optional_initial():
    class G(GoodConf):
        a: Optional[str]

    initial = G().get_initial()
    assert initial["a"] is None
