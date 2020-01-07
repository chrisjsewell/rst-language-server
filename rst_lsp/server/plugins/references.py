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
    # exclude the declaration of the current symbol

    database = document.workspace.database
    uri = document.uri
    result = database.query_at_position(
        uri=uri,
        line=position["line"],
        character=position["character"],
        load_references=True,
    )

    if result is None:
        return []

    # TODO handle specific roles/directives, e.g. :ref: and :cite:

    # capture:
    # target
    # target -> reference
    # reference
    # reference -> target
    # reference -> target -> reference

    locations = []
    for target in result.targets:
        if not exclude_declaration:
            locations.append(_get_position_dict(target.position))
        for reference in target.references:
            locations.append(_get_position_dict(reference.position))
    for reference in result.references:
        if not exclude_declaration:
            locations.append(_get_position_dict(reference.position))
        if reference.target:
            locations.append(_get_position_dict(reference.target.position))
            for reference in reference.target.references:
                locations.append(_get_position_dict(reference.position))

    return locations


def _get_position_dict(position):
    return {
        "uri": position.uri,
        "range": {
            "start": {"line": position.startLine, "character": position.startCharacter},
            "end": {"line": position.endLine, "character": position.endCharacter},
        },
    }
