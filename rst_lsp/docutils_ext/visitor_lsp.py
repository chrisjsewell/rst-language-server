"""This module provides ``docutils.nodes.GenericNodeVisitor`` subclasses,
which generates JSONable, 'database friendly', information about the document.
This can be used for fast-lookup of the position of elements in the document,
and to reference/target mappings.

See ``rst_lsp.sphinx_ext.main.assess_source`` for their use

"""
import logging
from typing import List, Optional
import uuid

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from docutils import nodes

from rst_lsp.docutils_ext.inliner_lsp import LSPInline
from rst_lsp.docutils_ext.block_lsp import LSPDirective, LSPBlockTarget, LSPSection
from rst_lsp.server.constants import SymbolKind
from rst_lsp.server.datatypes import DocumentSymbol


logger = logging.getLogger(__name__)


class VisitorRef2Target(nodes.GenericNodeVisitor):
    """Visitor to link references to their tagets.

    This is adapted from the code in
    ``transforms.references.Substitutions``,
    ``transforms.references.AnonymousHyperlinks``,
    ``transforms.references.Footnotes``,
    ``transforms.references.ExternalTargets``, and
    ``transforms.references.InternalTargets``.

    """

    def __init__(self, document):
        super().__init__(document)

        self.anonymous_targets = []
        self.anonymous_refs = []
        # TODO handle anonymous in VisitorLSP

        # assign ids to substitution definitions
        for sub_def_node in self.document.substitution_defs.values():
            sub_def_node["subdefid"] = self.get_uuid()

        # assign ids to citation definitions
        for citation_node in self.document.citations:
            citation_id = self.get_uuid()
            citation_node["citeid"] = citation_id
            for label in citation_node["names"]:
                if label in self.document.citation_refs:
                    for refnode in self.document.citation_refs[label]:
                        if "citerefid" not in refnode:
                            refnode["citerefid"] = citation_id

        # assign ids to footnote definitions
        for footnode_node in self.document.footnotes:
            foot_id = self.get_uuid()
            footnode_node["footid"] = foot_id
            for label in footnode_node["names"]:
                if label in self.document.footnote_refs:
                    for refnode in self.document.footnote_refs[label]:
                        if "footrefid" not in refnode:
                            refnode["footrefid"] = foot_id
        # TODO assign ids to auto-numbered / symbol footnote definitions

    def get_uuid(self):
        return str(uuid.uuid4())

    def default_visit(self, node):
        """Override for generic, uniform traversals."""
        pass

    def unknown_visit(self, node):
        """Override for generic, uniform traversals."""
        pass

    def visit_target(self, node):
        targetid = self.get_uuid()
        node["targetid"] = targetid
        if node.get("anonymous"):
            self.anonymous_targets.append(node)
            return
        for name in node["names"]:
            reflist = self.document.refnames.get(name, [])
            for ref in reflist:
                if "targetrefid" not in ref:
                    ref["targetrefid"] = targetid

    def visit_reference(self, node):
        if node.get("anonymous"):
            self.anonymous_refs.append(node)

    def visit_substitution_reference(self, node):
        refname = node["refname"]
        key = None
        if refname in self.document.substitution_defs:
            key = refname
        else:
            normed_name = refname.lower()
            # Mapping of case-normalized substitution names to case-sensitive names.
            key = self.document.substitution_names.get(normed_name, None)
        if key is None:
            self.document.reporter.warning(
                f'Undefined substitution referenced: "{refname}".', base_node=node
            )
            node["subrefid"] = False
        else:
            node["subrefid"] = self.document.substitution_defs[key]["subdefid"]

    def visit_citation_reference(self, node):
        if "citerefid" not in node:
            refname = node["refname"]
            classes = node.get("classes", None)
            if not node.get("classes", None):
                # sphinxcontrib-bibtex for example uses a citation_reference,
                # with node["classes"] = ["bibtex"]
                # and we don't want to raise warnings for this type of citation_reference
                self.document.reporter.warning(
                    f'Undefined citation referenced: "{refname}" {classes}.',
                    base_node=node,
                )
            node["citerefid"] = False


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
    targets: Optional[List[str]]
    # references that only apply to targets within the same document
    refs_samedoc: Optional[List[str]]
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
        self.block2idname = {
            "footnote": "footid",
            "citation": "citeid",
            "hyperlink_target": "targetid",
            "substitution_def": "subdefid",
        }
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
        elif isinstance(node, LSPBlockTarget):
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
            }
            if node.etype in self.block2idname:
                target = node.children[0].get(self.block2idname[node.etype], None)
                if target is not None:
                    data["targets"] = [target]
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
            isinstance(node, (LSPSection, LSPDirective, LSPBlockTarget))
            and node.line_end is not None
        ):
            self.nesting.exit_block(node)
        elif isinstance(node, LSPInline):
            for key in ["targets", "refs_samedoc"]:
                if key in self.current_inline:
                    self.current_inline[key] = list(self.current_inline[key])
            self.db_entries.append(self.current_inline)
            self.current_inline = None

    def default_visit(self, node):
        if self.current_inline is not None:
            for target_attr in ("footid", "citeid", "targetid", "subdefid"):
                if target_attr in node and node[target_attr]:
                    self.current_inline.setdefault("targets", set()).add(
                        node[target_attr]
                    )
            for ref_attr in ("footrefid", "citerefid", "targetrefid", "subrefid"):
                if ref_attr in node and node[ref_attr]:
                    self.current_inline.setdefault("refs_samedoc", set()).add(
                        node[ref_attr]
                    )

    def default_departure(self, node):
        pass
