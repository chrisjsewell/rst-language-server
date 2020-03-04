"""Thread local variants of mutable types, for creating threadsafe globals."""
from collections.abc import MutableMapping, MutableSet
import threading
import types
from typing import Optional


class ThreadLocalDict(MutableMapping):
    """A dictionary that gets/sets separate data for each thread."""

    def __init__(self, initial: Optional[MutableMapping] = None):
        self._thread_local = threading.local()
        if initial is not None:
            if not isinstance(initial, MutableMapping):
                raise AssertionError("`initial` must be a mutable mapping")
            self._thread_local.value = initial

    @property
    def _dict(self) -> MutableMapping:
        try:
            value = self._thread_local.value
        except AttributeError:
            self._thread_local.value = value = {}
        return value

    def _remove(self):
        if hasattr(self._thread_local, "value"):
            delattr(self._thread_local, "value")

    def __getitem__(self, item):
        return self._dict.__getitem__(item)

    def __setitem__(self, item, value):
        self._dict.__setitem__(item, value)

    def __delitem__(self, item):
        self._dict.__delitem__(item)

    def __iter__(self):
        return self._dict.__iter__()

    def __len__(self):
        return self._dict.__len__()

    def __str__(self):
        return self._dict.__str__()


class ThreadLocalSet(MutableSet):
    """A set that gets/sets separate data for each thread."""

    def __init__(self, initial: Optional[MutableSet] = None):
        self._thread_local = threading.local()
        if initial is not None:
            if not isinstance(initial, MutableSet):
                raise AssertionError("`initial` must be a mutable set")
            self._thread_local.value = initial

    @property
    def _set(self) -> MutableSet:
        try:
            value = self._thread_local.value
        except AttributeError:
            self._thread_local.value = value = set()
        return value

    def _remove(self):
        if hasattr(self._thread_local, "value"):
            delattr(self._thread_local, "value")

    def __contains__(self, item):
        return self._set.__contains__(item)

    def __iter__(self):
        return self._set.__iter__()

    def __len__(self):
        return self._set.__len__()

    def add(self, item):
        """Add an element."""
        return self._set.add(item)

    def discard(self, item):
        """Remove an element. Do not raise an exception if absent."""
        return self._set.discard(item)

    def __str__(self):
        return self._set.__str__()


class ThreadLocalMeta(type):
    """This metaclass makes setting additional attributes on the class thread local"""

    def __new__(mcs, name, bases, attributes):
        attributes["_thread_local_attrs"] = threading.local()
        new_class = super().__new__(mcs, name, bases, attributes)

        def make_func(class_new_method):
            """Create a __new__ function,
            that will set the local thread attributes on the new instance.
            """

            def _new_inst_patch(cls, *args, **kwargs):
                instance = class_new_method(cls)
                for name, value in getattr(
                    cls._thread_local_attrs, "value", {}
                ).items():
                    if callable(value):
                        # bind functions as methods
                        setattr(instance, name, types.MethodType(value, instance))
                    else:
                        setattr(instance, name, value)
                return instance

            return _new_inst_patch

        new_class.__new__ = make_func(new_class.__new__)
        return new_class

    def __getattr__(cls, name):
        """Called only for attributes that don't exist."""
        try:
            return cls._thread_local_attrs.value[name]
        except (AttributeError, KeyError):
            raise AttributeError(f"type object '{cls}' has no attribute '{name}'")

    def __setattr__(cls, name, value):
        """Called for all attributes."""
        if name == "__new__" and getattr(value, "__name__", None) == "_new_inst_patch":
            return super().__setattr__(name, value)
        if hasattr(cls, name) and name not in getattr(
            cls._thread_local_attrs, "value", {}
        ):
            raise AttributeError(
                f"Re-setting existing attribute '{name}' "
                f"is prohibited on type object '{cls}'"
            )
        else:
            try:
                cls._thread_local_attrs.value[name] = value
            except AttributeError:
                cls._thread_local_attrs.value = {}
                cls._thread_local_attrs.value[name] = value

    def __delattr__(cls, name):
        """Called for all attributes."""
        exists = hasattr(cls, name)
        if not exists:
            raise AttributeError(name)
        if exists and name not in getattr(cls._thread_local_attrs, "value", {}):
            raise AttributeError(
                f"Deletion of existing attribute '{name}' "
                f"is prohibited on type object '{cls}'"
            )
        cls._thread_local_attrs.value.pop(name)
