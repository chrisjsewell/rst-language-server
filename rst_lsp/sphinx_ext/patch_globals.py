"""Module to patch sphinx globals.

`sphinx.util.docutils.additional_nodes` is a mutable set,
that is added to then discarded, during a parse.

To guard against this being reset during parsing in one thread,
from another thread, here we patch it to be 'thread-local'.

Also see `rst_lsp.docutils_ext.patch_globals`
"""
from rst_lsp.thread_local import ThreadLocalSet
from sphinx.util.docutils import additional_nodes


additional_nodes = ThreadLocalSet(set(additional_nodes))
