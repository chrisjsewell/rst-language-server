"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
which generates JSONable, 'database friendly', information about the document
(stored in `self.db_entries`).

The vistor should be used on a document created using the PositionInliner
(i.e. containing `PosInline` elements), and ``document.walkabout(visitor)``
should be used, so that the departure method is called.
"""
from typing import Optional

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

import uuid

from docutils import nodes

from rst_lsp.docutils_ext.inliner_pos import PosInline
from rst_lsp.docutils_ext.block_pos import PosDirective, PosExplicit, PosSection
from rst_lsp.server.constants import SymbolKind


class DBElement(TypedDict):
    uuid: str
    parent_uuid: Optional[str]
    block: bool
    type: str
    startLine: int
    startCharacter: int
    endLine: int
    endCharacter: int
    # then element specific data


ELEMENT2KIND = {
    # inlines
    "ref_basic": SymbolKind.Property,
    "ref_anon": SymbolKind.Property,
    "ref_cite": SymbolKind.Property,
    "ref_foot": SymbolKind.Property,
    "ref_sub": SymbolKind.Property,
    "ref_phrase": SymbolKind.Property,
    "target_inline": SymbolKind.Field,
    "role": SymbolKind.Function,
    # blocks
    "section": SymbolKind.Module,
    "directive": SymbolKind.Class,
    "footnote": SymbolKind.Field,
    "citation": SymbolKind.Field,
    "hyperlink_target": SymbolKind.Field,
    "substitution_def": SymbolKind.Field,
}


class NestedElements:
    """This class keeps a record of the current elements entered."""

    def __init__(self):
        self._elements = []

    def enter_block(self, node, uuid_value: str):
        node.uuid_value = uuid_value
        self._elements.append(uuid_value)

    def exit_block(self, node):
        try:
            if self._elements[-1] != node.uuid_value:
                raise AssertionError("Exiting a non-leaf element")
        except AttributeError:
            raise AssertionError("node property 'uuid_value' not set")
        self._elements.pop()
        del node.uuid_value

    @property
    def parent_uuid(self):
        return None if not self._elements else self._elements[-1]


class VisitorLSP(nodes.GenericNodeVisitor):
    """Extract information, to generate data for Language Service Providers."""

    def __init__(self, document, source):
        super().__init__(document)
        self.source_lines = source.splitlines()
        self.db_entries = []
        self.nesting = NestedElements()
        self.current_inline = None

    def get_uuid(self):
        return str(uuid.uuid4())

    def get_block_range(self, start_indx, end_indx, indent_start=True):
        """Return the range of a block."""
        start_line = self.source_lines[start_indx]
        start_column = 0
        if indent_start:
            start_column = len(start_line) - len(start_line.lstrip())
        last_indx = len(self.source_lines) - 1
        end_indx = last_indx if end_indx > last_indx else end_indx
        end_column = len(self.source_lines[end_indx]) - 1
        end_column = 0 if end_column < 0 else end_column
        return (start_indx, start_column, end_indx, end_column)

    def unknown_visit(self, node):
        """Override for generic, uniform traversals."""
        if isinstance(node, PosSection) and node.line_end is not None:
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            self.db_entries.append(
                {
                    "uuid": uuid_value,
                    "parent_uuid": self.nesting.parent_uuid,
                    "block": True,
                    "type": "section",
                    "startLine": start_indx,
                    "startCharacter": start_column,
                    "endLine": end_indx,
                    "endCharacter": end_column,
                    "level": node.level,
                }
            )
            self.nesting.enter_block(node, uuid_value)
        elif isinstance(node, PosDirective):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            self.db_entries.append(
                {
                    "uuid": uuid_value,
                    "parent_uuid": self.nesting.parent_uuid,
                    "block": True,
                    "type": "directive",
                    "startLine": start_indx,
                    "startCharacter": start_column,
                    "endLine": end_indx,
                    "endCharacter": end_column,
                    "contentLine": node.line_content,
                    "contentCharacter": node.content_indent + start_indx
                    if node.content_indent
                    else None,
                    "dname": node.dname,
                    "arguments": node.arguments,
                    "options": node.options,
                    "klass": node.klass,
                }
            )
            self.nesting.enter_block(node, uuid_value)
        elif isinstance(node, PosExplicit):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            self.db_entries.append(
                {
                    "uuid": uuid_value,
                    "parent_uuid": self.nesting.parent_uuid,
                    "block": True,
                    "type": node.etype,
                    "startLine": start_indx,
                    "startCharacter": start_column,
                    "endLine": end_indx,
                    "endCharacter": end_column,
                    "names": node.children[0].attributes.get("names")
                    if node.children
                    else None,
                }
            )
            self.nesting.enter_block(node, uuid_value)
        elif isinstance(node, PosInline):
            sline, scol, eline, ecol = node.attributes["position"]
            data = {
                "uuid": self.get_uuid(),
                "parent_uuid": self.nesting.parent_uuid,
                "block": False,
                "type": node.attributes["type"],
                "startLine": sline,
                "startCharacter": scol,
                "endLine": eline,
                "endCharacter": ecol,
            }
            if "role" in node.attributes:
                data["rname"] = node.attributes["role"]
            self.current_inline = data

    def unknown_departure(self, node):
        """Override for generic, uniform traversals."""
        if isinstance(node, (PosSection, PosDirective, PosExplicit)):
            self.nesting.exit_block(node)
        elif isinstance(node, PosInline):
            for key in ["ids", "names", "refnames"]:
                if key in self.current_inline:
                    self.current_inline[key] = list(self.current_inline[key])
            self.db_entries.append(self.current_inline)
            self.current_inline = None

    def default_visit(self, node):
        # TODO split into explicit node type visits
        if self.current_inline is not None and hasattr(node, "attributes"):
            # ids = node.attributes.get("ids", None)
            # if ids:
            #     self.current_data.setdefault("ids", set()).update(ids)
            names = node.attributes.get("names", None)
            if names:
                self.current_inline.setdefault("names", set()).update(names)
            refname = node.attributes.get("refname", None)
            if refname:
                self.current_inline.setdefault("refnames", set()).add(refname)

    def default_departure(self, node):
        pass
