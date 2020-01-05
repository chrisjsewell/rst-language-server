"""Module to patch docutils globals.

During a parse, docutils lazy loads available roles/directives into the globals
``_directives`` and ``_roles``. A Sphinx parse is run within a context manager
(``sphinx.util.docutils.docutils_namespace``)
that saves the initial state of these globals and resets it on exit.

To guard against the globals being reset during parsing in one thread,
from another thread, here we patch these globals to be 'thread-local'.

Additionally, Sphinx sets/deletes `visit_`/`depart_` methods on the
`GenericNodeVisitor` and `SparseNodeVisitor` classes, so we replace
these classes with a sub-class that ensures thread local `setattr`/`delattr`

Also see `rst_lsp.sphinx_ext.patch_globals`
"""
from docutils import nodes
from docutils.parsers.rst import directives, roles

from rst_lsp.thread_local import ThreadLocalDict, ThreadLocalMeta


roles._roles = ThreadLocalDict(roles._roles)
directives._directives = ThreadLocalDict(directives._directives)


class GenericNodeVisitorTLocal(nodes.GenericNodeVisitor, metaclass=ThreadLocalMeta):
    pass


class SparseNodeVisitorTLocal(nodes.SparseNodeVisitor, metaclass=ThreadLocalMeta):
    pass


nodes.GenericNodeVisitor = GenericNodeVisitorTLocal
nodes.SparseNodeVisitor = SparseNodeVisitorTLocal
