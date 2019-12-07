"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
which generates JSONable, 'database friendly', information about the document
(stored in `self.db_entries`).

The vistor should be used on a document created using the PositionInliner
(i.e. containing `PosInline` elements), and ``document.walkabout(visitor)``
should be used, so that the departure method is called.
"""
import uuid

from docutils import nodes

from rst_lsp.docutils_ext.inliner_pos import PosInline
from rst_lsp.docutils_ext.block_pos import PosDirective, PosExplicit, PosSection


class CurrentSections:
    """This class keeps a record of the current sections, for the visitor."""

    def __init__(self):
        self._sections = []

    def enter_section(self, level: int, uuid: str):
        if len(self._sections) != level - 1:
            raise ValueError(
                f"Section level {level} not complicit with current sections: "
                f"{self._sections}"
            )
        self._sections.append(uuid)

    def exit_section(self, level: int):
        self._sections = self._sections[: level - 1]

    @property
    def uuid(self):
        return None if not self._sections else self._sections[-1]


class DatabaseVisitor(nodes.GenericNodeVisitor):
    """Extract information from the document, to generate a database."""

    def __init__(self, document, source):
        super().__init__(document)
        self.source_lines = source.splitlines()
        self.db_entries = []
        self.current_sections = CurrentSections()
        self.current_data = None

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
            section_uuid = self.current_sections.uuid
            my_uuid = str(uuid.uuid4())
            self.current_sections.enter_section(node.level, my_uuid)
            self.db_entries.append(
                {
                    "uuid": my_uuid,
                    "section_uuid": section_uuid,
                    "line_start": start_indx,
                    "column_start": start_column,
                    "line_end": end_indx,
                    "column_end": end_column,
                    "level": node.level,
                    "type": "section",
                    "block": True,
                }
            )
        elif isinstance(node, PosDirective):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            self.db_entries.append(
                {
                    "uuid": str(uuid.uuid4()),
                    "section_uuid": self.current_sections.uuid,
                    "line_start": start_indx,
                    "column_start": start_column,
                    "line_end": end_indx,
                    "column_end": end_column,
                    "line_content": node.line_content,
                    "column_content": node.content_indent + start_indx
                    if node.content_indent
                    else None,
                    "block": True,
                    "type": "directive",
                    "dname": node.dname,
                    "arguments": node.arguments,
                    "options": node.options,
                    "klass": node.klass,
                }
            )
        elif isinstance(node, PosExplicit):
            start_indx, start_column, end_indx, end_column = self.get_block_range(
                node.line_start, node.line_end
            )
            data = {
                "uuid": str(uuid.uuid4()),
                "section_uuid": self.current_sections.uuid,
                "line_start": start_indx,
                "column_start": start_column,
                "line_end": end_indx,
                "column_end": end_column,
                "type": node.etype,
                "names": node.children[0].attributes.get("names")
                if node.children
                else None,
                "block": True,
            }
            self.db_entries.append(data)
        elif isinstance(node, PosInline):
            sline, scol, eline, ecol = node.attributes["position"]
            data = {
                "uuid": str(uuid.uuid4()),
                "section_uuid": self.current_sections.uuid,
                "line_start": sline,
                "column_start": scol,
                "line_end": eline,
                "column_end": ecol,
                "type": node.attributes["type"],
                "block": False,
            }
            if "role" in node.attributes:
                data["rname"] = node.attributes["role"]
            self.current_data = data

    def unknown_departure(self, node):
        """Override for generic, uniform traversals."""
        if isinstance(node, PosSection):
            self.current_sections.exit_section(node.level)
        elif isinstance(node, PosInline):
            for key in ["ids", "names", "refnames"]:
                if key in self.current_data:
                    self.current_data[key] = list(self.current_data[key])

            self.db_entries.append(self.current_data)
            self.current_data = None

    def default_visit(self, node):
        # TODO split into explicit node type visits
        if self.current_data is not None and hasattr(node, "attributes"):
            # ids = node.attributes.get("ids", None)
            # if ids:
            #     self.current_data.setdefault("ids", set()).update(ids)
            names = node.attributes.get("names", None)
            if names:
                self.current_data.setdefault("names", set()).update(names)
            refname = node.attributes.get("refname", None)
            if refname:
                self.current_data.setdefault("refnames", set()).add(refname)

    def default_departure(self, node):
        pass
