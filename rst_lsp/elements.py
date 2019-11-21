"""These are effectively a copy of the standard docutils element,
but only containing JSON friendly data, to store in the database.
"""
import attr
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


@attr.s(kw_only=True)
class BlockElement:
    lineno: int = attr.ib()
    start_char = attr.ib(None)


@attr.s(kw_only=True)
class SectionElement(BlockElement):
    level: int = attr.ib()
    length: int = attr.ib()
    # node


@attr.s(kw_only=True)
class DirectiveElement(BlockElement):
    arguments: str = attr.ib()
    options: int = attr.ib()
    klass: str = attr.ib()
    # indented
