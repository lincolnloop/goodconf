from pydantic.fields import FieldInfo, Undefined


def _default_for_initial(f: FieldInfo):
    if f.default is not Undefined and f.default is not ...:
        return f.default
    return ""


class Value(FieldInfo):
    def __init__(self, *args, **kwargs):
        if "initial" in kwargs:
            if not callable(kwargs["initial"]):
                raise ValueError("Initial value must be a callable.")
        # default pydantic behavior
        default = kwargs.pop("default", Undefined)
        if default is not ... and kwargs.get("default_factory") is not None:
            raise ValueError('cannot specify both default and default_factory')
        super().__init__(default, **kwargs)

    @property
    def initial(self):
        if "initial" in self.extra:
            return self.extra["initial"]()
        return _default_for_initial(self)
