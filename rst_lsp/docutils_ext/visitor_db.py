"""This module provides a ``docutils.nodes.GenericNodeVisitor`` subclass,
which generates JSONable, 'database friendly', information about the document
(stored in `self.db_entries`).

The vistor should be used on a document created using the PositionInliner
(i.e. containing `PosInline` elements), and ``document.walkabout(visitor)``
should be used, so that the departure method is called.
"""

from docutils import nodes

from rst_lsp.docutils_ext.inliner_doc import PosInline


class DatabaseVisitor(nodes.GenericNodeVisitor):
    """Extract information from the document, to generate a database."""

    def __init__(self, document, source):
        super().__init__(document)
        self.db_entries = []
        self.current_data = None

    def unknown_visit(self, node):
        """Override for generic, uniform traversals."""
        if isinstance(node, PosInline):
            sline, scol, eline, ecol = node.attributes["position"]
            data = {
                "line_start": sline,
                "column_start": scol,
                "line_end": eline,
                "column_end": ecol,
                "type": node.attributes["type"],
                "block": False,
            }
            if "role" in node.attributes:
                data["role"] = node.attributes["role"]
            self.current_data = data

    def unknown_departure(self, node):
        """Override for generic, uniform traversals."""
        if isinstance(node, PosInline):
            for key in ["ids", "names", "refnames"]:
                if key in self.current_data:
                    self.current_data[key] = list(self.current_data[key])

            self.db_entries.append(self.current_data)
            self.current_data = None

    def default_visit(self, node):
        # TODO split into explicit node type visits
        if self.current_data is not None and hasattr(node, "attributes"):
            ids = node.attributes.get("ids", None)
            if ids:
                self.current_data.setdefault("ids", set()).update(ids)
            names = node.attributes.get("names", None)
            if names:
                self.current_data.setdefault("names", set()).update(names)
            refname = node.attributes.get("refname", None)
            if refname:
                self.current_data.setdefault("refnames", set()).add(refname)

    def default_departure(self, node):
        pass
