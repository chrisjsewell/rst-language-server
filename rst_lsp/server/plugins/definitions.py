import logging
from typing import List

from rst_lsp.server.datatypes import Position, Location
from rst_lsp.server.workspace import Config, Document
from rst_lsp.server.plugin_manager import hookimpl

logger = logging.getLogger(__name__)


@hookimpl
def rst_definitions(
    config: Config, document: Document, position: Position
) -> List[Location]:

    database = document.workspace.database
    uri = document.uri
    results = database.query_elements(
        uri=uri, startLine=position["line"], has_keys=["refs_samedoc"]
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
    for element in (
        database.query_targets(uri=uri, refs_samedoc=result["refs_samedoc"]) or []
    ):
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
