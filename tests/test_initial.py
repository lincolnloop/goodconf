from typing import Optional

import pytest

from goodconf import Field, GoodConf, initial_for_field

from .utils import KEY


def test_initial():
    class C(GoodConf):
        f: str = Field(initial=lambda: "x")

    assert initial_for_field(KEY, C.model_fields["f"]) == "x"


def test_initial_bad():
    class C(GoodConf):
        f: str = Field(initial="x")

    with pytest.raises(ValueError):
        initial_for_field(KEY, C.model_fields["f"])


def test_initial_default():
    class C(GoodConf):
        f: str = Field("x")

    assert initial_for_field(KEY, C.model_fields["f"]) == "x"


def test_initial_default_factory():
    class C(GoodConf):
        f: str = Field(default_factory=lambda: "y")

    assert initial_for_field(KEY, C.model_fields["f"]) == "y"


def test_no_initial():
    class C(GoodConf):
        f: str = Field()

    assert initial_for_field(KEY, C.model_fields["f"]) == ""


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
