import json

import pytest

from goodconf import Field, GoodConf, initial_for_field

from .utils import KEY


def test_initial() -> None:
    class C(GoodConf):
        f: str = Field(initial=lambda: "x")

    assert initial_for_field(KEY, C.model_fields["f"]) == "x"


def test_initial_does_not_break_json_schema() -> None:
    """The initial callable lives in metadata, not json_schema_extra, so
    schema generation stays serialisable."""

    class C(GoodConf):
        f: str = Field(initial=lambda: "x", default="d")

    assert json.dumps(C.model_json_schema())


def test_initial_bad() -> None:
    class C(GoodConf):
        f: str = Field(initial="x")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="callable"):
        initial_for_field(KEY, C.model_fields["f"])


def test_initial_default() -> None:
    class C(GoodConf):
        f: str = Field("x")

    assert initial_for_field(KEY, C.model_fields["f"]) == "x"


def test_initial_default_factory() -> None:
    class C(GoodConf):
        f: str = Field(default_factory=lambda: "y")

    assert initial_for_field(KEY, C.model_fields["f"]) == "y"


def test_no_initial() -> None:
    class C(GoodConf):
        f: str = Field()

    assert initial_for_field(KEY, C.model_fields["f"]) == ""


def test_default_initial() -> None:
    """Can get initial when Field is not used"""

    class G(GoodConf):
        a: str = "test"

    initial = G().get_initial()
    assert initial["a"] == "test"


def test_optional_initial() -> None:
    class G(GoodConf):
        a: str | None

    initial = G.get_initial()
    assert initial["a"] is None
