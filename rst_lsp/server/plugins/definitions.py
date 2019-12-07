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
        etype=("ref_basic", "ref_cite", "ref_foot", "ref_sub", "ref_phrase"),
        uri=uri,
        startLine=position["line"],
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
    if not found_result or not result.get("refnames", None):
        return []
    locations = []
    etypes = {"ref_sub": ("substitution_def",), "ref_foot": ("footnote",)}.get(
        result["type"], ("hyperlink_target", "target_inline", "section")
    )
    for element in (
        database.query_references(refnames=result["refnames"], etypes=etypes) or []
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
