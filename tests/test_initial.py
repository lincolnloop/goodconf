from typing import Optional

import pytest
from pydantic import BaseModel

from goodconf import Field, GoodConf, initial_for_field

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


def test_complex_initial():
    """Test a nested inner BaseModel"""

    class G(GoodConf):
        class A(BaseModel):
            inner: str = "test A"

        outer_a = A()

    initial = G().get_initial()
    assert initial["outer_a"]["inner"] == "test A"


def test_list_initial():
    """Test a list of basic types"""

    class G(GoodConf):
        list = [0, 1, 2]

    initial = G().get_initial()
    assert len(initial["list"]) == 3


def test_list_complex_initial():
    """Test a list of nested inner BaseModel"""

    class G(GoodConf):
        class A(BaseModel):
            inner: str = "test A"

        list = [A()]

    initial = G().get_initial()
    assert len(initial["list"]) == 1
    assert initial["list"][0]["inner"] == "test A"
