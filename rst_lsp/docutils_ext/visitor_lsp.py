"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
which generates JSONable, 'database friendly', information about the document
(stored in `self.db_entries`).

The vistor should be used on a document created using the PositionInliner
(i.e. containing `LSPInline` elements), and ``document.walkabout(visitor)``
should be used, so that the departure method is called.
"""
# TODO formalise references link to definitions,
# probably by applying docutils/docutils/transforms/references.py
import logging
from typing import List, Optional
import uuid

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from docutils import nodes

from rst_lsp.docutils_ext.inliner_lsp import LSPInline
from rst_lsp.docutils_ext.block_lsp import LSPDirective, LSPExplicit, LSPSection
from rst_lsp.server.constants import SymbolKind
from rst_lsp.server.datatypes import DocumentSymbol


logger = logging.getLogger(__name__)


class DBElement(TypedDict):
    uuid: str
    parent_uuid: Optional[str]
    block: bool
    type: str
    title: str
    startLine: int
    startCharacter: int
    endLine: int
    endCharacter: int
    # then element specific data
    # TODO use TypedDict with undefined keys?


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
        self._entered_uuid = []
        self._doc_symbols = []  # type: List[DocumentSymbol]

    def enter_block(self, node, data: DBElement):
        # logger.debug(f"entering node: {node}")
        uuid_value = data["uuid"]
        node.uuid_value = uuid_value  # this is used to check consistency of exits
        self._add_doc_symbols(data)
        self._entered_uuid.append(uuid_value)

    def exit_block(self, node):
        # logger.debug(f"exiting node: {node}")
        try:
            if self._entered_uuid[-1] != node.uuid_value:
                raise AssertionError("Exiting a non-leaf element")
        except AttributeError:
            raise AssertionError("node property 'uuid_value' not set")
        self._entered_uuid.pop()
        del node.uuid_value

    def add_inline(self, data: DBElement):
        self._add_doc_symbols(data)

    def _add_doc_symbols(self, data: DBElement):
        current_parent = self._doc_symbols
        for _ in self._entered_uuid:
            current_parent = current_parent[-1].setdefault("children", [])
        current_parent.append(
            {
                "name": data["title"],
                "detail": f'type: {data["type"]}',
                "kind": ELEMENT2KIND.get(data["type"], SymbolKind.Constant),
                "range": {
                    "start": {
                        "line": data["startLine"],
                        "character": data["startCharacter"],
                    },
                    "end": {"line": data["endLine"], "character": data["endCharacter"]},
                },
                # TODO only select first line?
                "selectionRange": {
                    "start": {
                        "line": data["startLine"],
                        "character": data["startCharacter"],
                    },
                    "end": {"line": data["endLine"], "character": data["endCharacter"]},
                },
            }
        )

    @property
    def parent_uuid(self):
        return None if not self._entered_uuid else self._entered_uuid[-1]

    @property
    def document_symbols(self) -> List[DocumentSymbol]:
        return self._doc_symbols


class VisitorLSP(nodes.GenericNodeVisitor):
    """Extract information, to generate data for Language Service Providers."""

    def __init__(self, document, source):
        super().__init__(document)
        self.source_lines = source.splitlines()
        self.db_entries = []
        self.nesting = NestedElements()
        self.current_inline = None
        # TODO add option to remove LSP nodes

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
        if isinstance(node, LSPSection) and node.line_end is not None:
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            data = {
                "uuid": uuid_value,
                "title": node.title,
                "parent_uuid": self.nesting.parent_uuid,
                "block": True,
                "type": "section",
                "startLine": start_indx,
                "startCharacter": start_column,
                "endLine": end_indx,
                "endCharacter": end_column,
                "level": node.level,
            }
            # ids = node.children[0].attributes.get("ids", [])
            # if ids:
            #     data["names"] = ids
            self.db_entries.append(data)
            self.nesting.enter_block(node, data)
        elif isinstance(node, LSPDirective):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            data = {
                "uuid": uuid_value,
                "title": node.dname,
                "parent_uuid": self.nesting.parent_uuid,
                "block": True,
                "type": "directive",
                "startLine": start_indx,
                "startCharacter": start_column,
                "endLine": end_indx,
                "endCharacter": end_column,
                "dtype": node.dname,
                "contentLine": node.line_content,
                "contentIndent": node.content_indent + start_column
                if node.content_indent
                else None,
                "arguments": node.arguments,
                "options": node.options,
                "klass": node.klass,
            }
            self.db_entries.append(data)
            self.nesting.enter_block(node, data)
        elif isinstance(node, LSPExplicit):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            uuid_value = self.get_uuid()
            data = {
                "uuid": uuid_value,
                "title": node.etype,
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
            self.db_entries.append(data)
            self.nesting.enter_block(node, data)
        elif isinstance(node, LSPInline):
            sline, scol, eline, ecol = node.attributes["position"]
            data = {
                "uuid": self.get_uuid(),
                "title": node.attributes["type"],
                "parent_uuid": self.nesting.parent_uuid,
                "block": False,
                "type": node.attributes["type"],
                "startLine": sline,
                "startCharacter": scol,
                "endLine": eline,
                "endCharacter": ecol,
            }
            if "role" in node.attributes:
                data["title"] = node.attributes["role"]
                data["rtype"] = node.attributes["role"]
            self.current_inline = data
            self.nesting.add_inline(data)

    def unknown_departure(self, node):
        """Override for generic, uniform traversals."""
        if (
            isinstance(node, (LSPSection, LSPDirective, LSPExplicit))
            and node.line_end is not None
        ):
            self.nesting.exit_block(node)
        elif isinstance(node, LSPInline):
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
