from typing import List

from rst_lsp.server.datatypes import DocumentSymbol
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.plugin_manager import hookimpl


@hookimpl
def rst_document_symbols(
    config: Config, workspace: Workspace, document: Document
) -> List[DocumentSymbol]:

    database = workspace.database
    uri = document.uri
    return database.query_doc_symbols(uri=uri) or []
