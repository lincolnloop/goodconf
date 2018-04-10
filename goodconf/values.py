import os
from typing import TypeVar, Callable
from decimal import Decimal

from distutils.util import strtobool

CASTS = [int, str, float, list, bool, Decimal]
CastTypes = TypeVar('CastTypes', *CASTS)


class RequiredValueMissing(Exception):
    pass


class Value:
    def __init__(self, key: str=None, default=None,
                 initial: Callable[[], CastTypes] = None,
                 cast_as: CastTypes = None, help: str = ""):
        """
        :param key:      Name of the value used in file or environment
                         variable. Set automatically by the GoodConf metaclass.
        :param default:  Default value if none is provided. If left unset,
                         loading a config thait fails to provide this value
                         will raise a RequiredValueMissing exception.
        :param initial:  Initial value to use when generating a config
        :param cast_as:  Python type to cast variable as. Defaults to type of
                         default (if provided) or str.
        :param help:     Plain-text description of the value.
        """
        self.key = key
        self.default = default
        self.initial = initial
        self.help = help
        if cast_as:
            self.cast_as = cast_as
        elif default is not None:
            self.cast_as = type(default)
        else:
            self.cast_as = str

    @property
    def required(self):
        return self.default is None

    @property
    def value(self):
        if self.key in os.environ:
            self._value = self.cast(os.environ[self.key])
        if not hasattr(self, '_value'):
            self._value = self.default
            if callable(self._value):
                self._value = self._value()
        return self._value

    @value.setter
    def value(self, value):
        if value is None:
            if self.required:
                raise RequiredValueMissing(self.key)
            del self.value
        else:
            self._value = value

    @value.deleter
    def value(self):
        if hasattr(self, '_value'):
            del self._value

    @property
    def initial(self):
        return self._initial() if self._initial else self.default or ''

    @initial.setter
    def initial(self, value):
        if value and not callable(value):
            raise ValueError("Initial value must be a callable.")
        self._initial = value

    def __get__(self, instance, owner):
        if instance is None:
            # Accessing via the class. Return the initial value (falling
            # back to default).
            return self.initial
        return self.value

    def __set__(self, instance, value):
        self.value = value

    def __delete__(self, instance):
        del self.value

    def cast(self, val: str):
        """converts string to type requested by `cast_as`"""
        try:
            return getattr(self, 'cast_as_{}'.format(
                self.cast_as.__name__.lower()))(val)
        except AttributeError:
            return self.cast_as(val)

    def cast_as_list(self, val: str) -> list:
        """Convert a comma-separated string to a list"""
        return val.split(',')

    def cast_as_bool(self, val: str) -> bool:
        """
        True values are y, yes, t, true, on and 1
        False values are n, no, f, false, off and 0
        Raises ValueError if val is anything else.
        """
        return bool(strtobool(val))
