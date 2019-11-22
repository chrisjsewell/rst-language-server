"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
that extracts ``InfoNodeBlock`` and ``InfoNodeInline`` elements,
to generate a JSONable, 'database friendly', representation of elements in the doctree
(stored in `DocInfoVisitor.info_datas`).
"""
from enum import Enum

from docutils import nodes

from rst_lsp.docutils_ext.inliner import InfoNodeInline
from rst_lsp.docutils_ext.parser import InfoNodeBlock


class ElementType(Enum):
    section = "section"
    directive = "directive"
    role = "role"
    link = "link"
    reference = "reference"
    internal_target = "internal_target"


class DocInfoVisitor(nodes.GenericNodeVisitor):
    """Extract info nodes from the document."""

    def __init__(self, document, source):
        super().__init__(document)
        self.info_datas = []
        self.lines = source.splitlines()

    def unknown_visit(self, node):
        """Override for generic, uniform traversals."""
        # NOTE and line and character offsets should be zero-based
        if isinstance(node, InfoNodeBlock):
            if node.dtype == "section":
                self.info_datas.append(
                    {
                        "type": "Block",
                        "element": ElementType.section.value,
                        "start_char": 0,
                        "lineno": node.doc_lineno - 1,
                        "level": node.other_data["level"],
                        "title": node.other_data["title"],
                    }
                )
            elif node.dtype == "directive":
                line = self.lines[node.doc_lineno - 1]
                self.info_datas.append(
                    {
                        "type": "Block",
                        "element": ElementType.directive.value,
                        "start_char": len(line) - len(line.lstrip()),
                        "lineno": node.doc_lineno - 1,
                        "type_name": node.other_data["type_name"],
                        "klass": node.other_data["klass"],
                        "arguments": node.other_data["arguments"],
                        "options": node.other_data["options"],
                    }
                )
            elif node.dtype == "explicit_construct":
                # one of "footnote", "citation",  "hyperlink_target", "substitution_def"
                next_node = node.next_node(siblings=True)
                info = {
                    "type": "Block",
                    "element": node.other_data["ctype"],
                    "start_char": 0,
                    "lineno": node.doc_lineno - 1,
                    "raw": node.other_data["raw"],
                }
                try:
                    if node.other_data["ctype"] == "hyperlink_target":
                        info["target"] = next_node.attributes["ids"][0]
                    elif node.other_data["ctype"] == "substitution_def":
                        info["sub"] = next_node.attributes["names"][0]
                except IndexError:
                    pass
                self.info_datas.append(info)

        elif isinstance(node, InfoNodeInline):
            if node.dtype == "phrase_ref":
                # followed by reference, then optionally by target
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.link.value,
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                        "alias": node.other_data["alias"],
                        "raw": node.other_data["raw"],
                    }
                )
            elif node.dtype == "role":
                # followed by nodes created by role function
                # (or problematic, if the role does not exist)
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.role.value,
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                        "role": node.other_data["role"],
                        "content": node.other_data["content"],
                        "raw": node.other_data["raw"],
                    }
                )
            elif node.dtype == "inline_internal_target":
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.internal_target.value,
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                    }
                )
            elif node.dtype == "substitution_reference":
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.reference.value,
                        "ref_type": "substitution",
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                    }
                )
            elif node.dtype == "footnote_reference":
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.reference.value,
                        "ref_type": "footnote",
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                    }
                )
            elif node.dtype in ["anonymous_reference", "std_reference"]:
                self.info_datas.append(
                    {
                        "type": "Inline",
                        "element": ElementType.reference.value,
                        "ref_type": "anonymous",
                        "lineno": node.doc_lineno - 1,
                        "start_char": node.doc_char,
                        "refname": node.other_data["refname"],
                        "raw": node.other_data["raw"],
                    }
                )
            else:
                raise TypeError(f"unknown InfoNodeInline.dtype = {node.dtype}")
            node.parent.remove(node)

    def unknown_departure(self, node):
        """Override for generic, uniform traversals."""
        pass

    def default_visit(self, node):
        pass

    def default_departure(self, node):
        pass
