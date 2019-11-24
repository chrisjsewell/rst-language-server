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

    database = document.database
    uri = document.uri
    results = []

    results.append(
        {
            "name": "test",
            "detail": "Some detail",
            "kind": SymbolKind.Namespace,
            "range": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 9, "character": 0},
            },
            "selectionRange": {
                "start": {"line": 0, "character": 0},
                "end": {"line": 9, "character": 0},
            },
            # children
        }
    )
    return results
