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
    elements = database.query_positions(uri=uri, block=True) or []
    # logger.debug(str(elements))
    results = [
        {
            "kind": "region",
            "startLine": element["startLine"],
            "startCharacter": element["startCharacter"],
            "endLine": element["endLine"],
            "endCharacter": element["endCharacter"],
        }
        for element in elements
    ]
    return results
