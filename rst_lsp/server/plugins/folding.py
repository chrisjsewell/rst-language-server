import logging
from typing import List

from rst_lsp.server.datatypes import FoldingRange
from rst_lsp.server.plugin_manager import hookimpl
from rst_lsp.server.workspace import Document

logger = logging.getLogger(__name__)


@hookimpl
def rst_folding_range(document: Document) -> List[FoldingRange]:

    database = document.workspace.database
    uri = document.uri
    doc = database.query_doc(uri=uri, load_positions=True)
    results = [
        {
            "kind": "region",
            "startLine": position.startLine,
            "startCharacter": position.startCharacter,
            "endLine": position.endLine,
            "endCharacter": position.endCharacter,
        }
        for position in doc.positions
        if position.block
    ]
    return results
