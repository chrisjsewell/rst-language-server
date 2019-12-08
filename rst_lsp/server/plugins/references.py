import logging
from typing import List

from rst_lsp.server.datatypes import Position, Location
from rst_lsp.server.workspace import Document
from rst_lsp.server.plugin_manager import hookimpl

logger = logging.getLogger(__name__)


@hookimpl
def rst_references(
    document: Document, position: Position, exclude_declaration: bool = False
) -> List[Location]:
    # Include the declaration of the current symbol
    database = document.workspace.database
    uri = document.uri
    results = (
        database.query_elements(
            uri=uri, startLine=position["line"], has_keys=["targets"]
        )
        or []
    )
    results += (
        database.query_elements(
            uri=uri, startLine=position["line"], has_keys=["refs_samedoc"]
        )
        or []
    )
    # TODO handle specific roles/directives, e.g. :ref: and :cite:
    found_result = False
    for result in results or []:
        if result["startCharacter"] <= position["character"] and (
            result["endLine"] != position["line"]
            or position["character"] <= result["endCharacter"]
        ):
            found_result = True
            break
    if not found_result:
        return []
    locations = []
    elements = (
        database.query_references(
            uri=uri, targets=result.get("refs_samedoc", []) + result.get("targets", [])
        )
        or []
    )
    # TODO also include targets
    for element in elements + [
        result
    ]:  # ([] if exclude_declaration and  else [result]):
        locations.append(
            {
                "uri": element["uri"],
                "range": {
                    "start": {
                        "line": element["startLine"],
                        "character": element["startCharacter"],
                    },
                    "end": {
                        "line": element["endLine"],
                        "character": element["endCharacter"],
                    },
                },
            }
        )

    return locations
