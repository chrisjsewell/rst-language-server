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
    result = database.query_at_position(
        uri=uri, line=position["line"], character=position["character"]
    )
    if result is None:
        return []

    # TODO handle specific roles/directives, e.g. :ref: and :cite:
    elements = database.query_definitions(uri=uri, position_uuid=result["uuid"])

    locations = []
    for element in elements:
        position = database.query_position_uuid(uuid=element["position_uuid"])
        if not position:
            continue
        locations.append(
            {
                "uri": position["uri"],
                "range": {
                    "start": {
                        "line": position["startLine"],
                        "character": position["startCharacter"],
                    },
                    "end": {
                        "line": position["endLine"],
                        "character": position["endCharacter"],
                    },
                },
            }
        )

    return locations
