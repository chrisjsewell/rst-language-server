from typing import List

from rst_lsp.docutils_ext.visitor import ElementType
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.datatypes import DocumentSymbol
from rst_lsp.server.constants import SymbolKind
from . import hookimpl


@hookimpl
def rst_document_symbols(
    config: Config, workspace: Workspace, document: Document
) -> List[DocumentSymbol]:

    database = workspace.database
    uri = document.uri
    results = []

    for section in database.query_elements(
        [ElementType.section.value], uri=uri, section_uuid=None
    ):
        title = section["title"]
        results.append(
            {
                "name": title,
                # "detail": "Some detail",
                "kind": SymbolKind.Module,
                "range": {
                    "start": {"line": section["lineno"], "character": 0},
                    "end": {"line": section["lineno"], "character": len(title) - 1},
                },
                "selectionRange": {
                    "start": {"line": section["lineno"], "character": 0},
                    "end": {"line": section["lineno"], "character": len(title) - 1},
                },
                "children": _create_children(section, uri, database),
            }
        )
    return results


def _create_children(section, uri, database):
    children = []
    for sub_section in database.query_elements(
        [ElementType.section.value], uri=uri, section_uuid=section["uuid"]
    ):
        title = sub_section["title"]
        children.append(
            {
                "name": title,
                # "detail": "Some detail",
                "kind": SymbolKind.Module,
                "range": {
                    "start": {"line": sub_section["lineno"], "character": 0},
                    "end": {"line": sub_section["lineno"], "character": len(title) - 1},
                },
                "selectionRange": {
                    "start": {"line": sub_section["lineno"], "character": 0},
                    "end": {"line": sub_section["lineno"], "character": len(title) - 1},
                },
                "children": _create_children(sub_section, uri, database),
            }
        )
    return children
