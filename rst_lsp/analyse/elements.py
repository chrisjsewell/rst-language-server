"""These are effectively a copy of the standard docutils element,
but only containing JSON friendly data, to store in the database.
"""
from docutils import nodes


class InfoNodeInline(nodes.Node):
    """A node for highlighting a position in the document."""

    def __init__(self, inliner, match, dtype, doc_lineno, doc_char, data={}):
        self.parent = inliner.parent
        self.document = inliner.document
        self.match = match
        self.dtype = dtype
        self.doc_lineno = doc_lineno
        self.doc_char = doc_char
        self.other_data = data or {}
        self.children = []

    def astext(self):
        return f"InfoNodeInline({self.dtype})"

    def pformat(self, indent="    ", level=0):
        """Return an indented pseudo-XML representation, for test purposes."""
        return indent * level + f"InfoNodeInline({self.dtype})\n"


class InfoNodeBlock(nodes.Node):
    """A node for highlighting a position in the document."""

    def __init__(self, dtype, doc_lineno, match=None, data={}):
        self.match = match
        self.dtype = dtype
        self.doc_lineno = doc_lineno
        self.other_data = data or {}
        self.children = []

    def astext(self):
        return f"InfoNodeBlock({self.dtype})"

    def pformat(self, indent="    ", level=0):
        """Return an indented pseudo-XML representation, for test purposes."""
        return indent * level + f"InfoNodeBlock({self.dtype})\n"
