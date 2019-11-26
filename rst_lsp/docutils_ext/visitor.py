"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
that extracts ``InfoNodeBlock`` and ``InfoNodeInline`` elements,
to generate a JSONable, 'database friendly', representation of elements in the doctree
(stored in `DocInfoVisitor.info_datas`).
"""
from enum import Enum
import uuid

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
        self.current_section = None
        self.sub_level_sections = {}

    def _add_block_info(self, element_type, dct):
        dct["element"] = element_type
        dct["type"] = "Block"
        dct["uuid"] = str(uuid.uuid4())
        if element_type == ElementType.section.value:
            if self.current_section is None:
                dct["section_uuid"] = None
                self.current_section = dct
                self.sub_level_sections[dct["level"]] = dct
            elif dct["level"] <= self.current_section["level"]:
                highest_sect = None
                for level, sub_dct in list(self.sub_level_sections.items()):
                    if level >= dct["level"]:
                        self.sub_level_sections.pop(level)
                    elif highest_sect is None or level > highest_sect["level"]:
                        highest_sect = sub_dct
                dct["section_uuid"] = (
                    None if highest_sect is None else highest_sect["uuid"]
                )
                self.current_section = dct
                self.sub_level_sections[dct["level"]] = dct
            else:
                dct["section_uuid"] = self.current_section["uuid"]
                self.current_section = dct
                self.sub_level_sections[dct["level"]] = dct
        else:
            dct["section_uuid"] = (
                None if self.current_section is None else self.current_section["uuid"]
            )
        self.info_datas.append(dct)

    def _add_inline_info(self, node, element_type, **kwargs):
        data = {
            "type": "Inline",
            "uuid": str(uuid.uuid4()),
            "element": element_type,
            "raw": node.raw,
            "lineno": node.doc_lineno - 1,
            "start_char": node.doc_char,
            "end_char": node.doc_char + len(node.raw),  # TODO adjust for multi-line?
            "section_uuid": None
            if self.current_section is None
            else self.current_section["uuid"],
        }
        assert not set(kwargs.keys()).intersection(data.keys())
        data.update(kwargs)
        self.info_datas.append(data)

    def unknown_visit(self, node):
        """Override for generic, uniform traversals."""
        # NOTE and line and character offsets should be zero-based
        if isinstance(node, InfoNodeBlock):
            if node.dtype == "section":
                self._add_block_info(
                    ElementType.section.value,
                    {
                        "start_char": 0,
                        "lineno": node.doc_lineno - 1,
                        "level": node.other_data["level"],
                        "title": node.other_data["title"],
                    },
                )
            elif node.dtype == "directive":
                line = self.lines[node.doc_lineno - 1]
                dlines = node.other_data["block_text"].rstrip().splitlines()
                endline = node.doc_lineno - 2 + len(dlines)
                self._add_block_info(
                    ElementType.directive.value,
                    {
                        "start_char": len(line) - len(dlines[0]),
                        "lineno": node.doc_lineno - 1,
                        "endline": endline,
                        "end_char": len(self.lines[endline]) - 1,
                        "type_name": node.other_data["type_name"],
                        "klass": node.other_data["klass"],
                        "arguments": node.other_data["arguments"],
                        "options": node.other_data["options"],
                    },
                )
            elif node.dtype == "explicit_construct":
                # one of "footnote", "citation",  "hyperlink_target", "substitution_def"
                next_node = node.next_node(siblings=True)
                info = {
                    "start_char": 0,  # TODO get proper start character (using raw?)
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
                self._add_block_info(node.other_data["ctype"], info)

        elif isinstance(node, InfoNodeInline):
            if node.dtype == "phrase_ref":
                # followed by reference, then optionally by target
                self._add_inline_info(
                    node, ElementType.link.value, alias=node.other_data["alias"],
                )
            elif node.dtype == "role":
                # followed by nodes created by role function
                # (or problematic, if the role does not exist)
                self._add_inline_info(
                    node,
                    ElementType.role.value,
                    role=node.other_data["role"],
                    content=node.other_data["content"],
                )
            elif node.dtype == "inline_internal_target":
                self._add_inline_info(
                    node, ElementType.internal_target.value,
                )
            elif node.dtype == "substitution_reference":
                self._add_inline_info(
                    node, ElementType.reference.value, ref_type="substitution",
                )
            elif node.dtype == "footnote_reference":
                self._add_inline_info(
                    node, ElementType.reference.value, ref_type="footnote",
                )
            elif node.dtype in ["anonymous_reference", "std_reference"]:
                self._add_inline_info(
                    node,
                    ElementType.reference.value,
                    ref_type="anonymous",
                    refname=node.other_data["refname"],
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
