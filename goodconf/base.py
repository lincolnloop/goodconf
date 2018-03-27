import copy
from collections import OrderedDict

from goodconf.values import Value


class DeclarativeValuesMetaclass(type):
    """
    Collect Values declared on the base classes.
    """

    def __new__(mcs, name, bases, attrs):
        # Collect values from current class.
        current_fields = []
        for key, value in list(attrs.items()):
            if isinstance(value, Value):
                if value.key and key != value.key:
                    raise AttributeError(
                        "Don't explicitly set keys when declaring values")
                value = copy.copy(value)
                value.key = key
                attrs[key] = value
                current_fields.append((key, value))
        values = OrderedDict(current_fields)
        attrs['_declared_values'] = OrderedDict(current_fields)

        new_class = super(DeclarativeValuesMetaclass, mcs).__new__(
            mcs, name, bases, attrs)

        # Walk through the MRO.
        values = OrderedDict()
        for base in new_class.__mro__:
            if not hasattr(base, '_declared_values'):
                continue
            # Add values from base class.
            for key, value in base._declared_values.items():
                if key not in values:
                    new_value = copy.copy(value)
                    new_value.__delete__(None)
                    values[key] = new_value

        new_class._values = values

        return new_class

    @classmethod
    def __prepare__(metacls, name, bases, **kwds):
        # Remember the order that values are defined.
        return OrderedDict()
