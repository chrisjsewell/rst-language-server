"""Module to patch docutils globals.

During a parse, docutils lazy loads available roles/directives into the globals
``_directives`` and ``_roles``. A Sphinx parse is run within a context manager
(``sphinx.util.docutils.docutils_namespace``)
that saves the initial state of these globals and resets it on exit.

To guard against the globals being reset during parsing in one thread,
from another thread, here we patch these globals to be 'thread-local'.

"""
import threading
from typing import Optional, MutableMapping

from docutils.parsers.rst import directives, roles


class ThreadLocalDict(MutableMapping):
    def __init__(self, initial: Optional[MutableMapping] = None):
        self._thread_local = threading.local()
        if initial is not None:
            if not isinstance(initial, MutableMapping):
                raise AssertionError("`initial` must be a mutable mapping")
            self._thread_local.value = initial

    @property
    def _dict(self):
        if not hasattr(self._thread_local, "value"):
            self._thread_local.value = {}
        return self._thread_local.value

    def remove(self):
        if not hasattr(self._thread_local, "value"):
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


roles._roles = ThreadLocalDict(roles._roles)
directives._directives = ThreadLocalDict(directives._directives)
