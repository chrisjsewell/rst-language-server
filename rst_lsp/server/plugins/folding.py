from typing import List

from rst_lsp.docutils_ext.visitor import ElementType
from rst_lsp.server.datatypes import FoldingRange
from rst_lsp.server.plugin_manager import hookimpl
from rst_lsp.server.workspace import Document


@hookimpl
def rst_folding_range(document: Document) -> List[FoldingRange]:

    database = document.workspace.database
    uri = document.uri
    results = []
    # TODO probably want startCharacter to be at the end of the startLine?
    # TODO can now utilise section_uuid

    # Get section folding
    doc_data = database.query_doc(uri)
    sections = database.query_elements(name=ElementType.section.value, uri=uri)
    start_stack = {}
    for section in sorted(sections or [], key=lambda d: d["lineno"]):
        for level, start in list(start_stack.items()):
            if level >= section["level"]:
                start = start_stack.pop(level)
                results.append(
                    {
                        "kind": "region",
                        "startLine": start["line"],
                        "startCharacter": start["char"],
                        "endLine": section["lineno"] - 1,
                        "endCharacter": 0,
                    }
                )
        start_stack[section["level"]] = {
            "line": section["lineno"],
            "char": section["start_char"],
        }
    for level, start in start_stack.items():
        results.append(
            {
                "kind": "region",
                "startLine": start["line"],
                "startCharacter": start["char"],
                "endLine": doc_data["endline"],
                "endCharacter": doc_data["endchar"],
            }
        )

    # Get directive folding
    # TODO unknown directives are not included in database
    directives = database.query_elements(name=ElementType.directive.value, uri=uri)
    for directive in directives or []:
        # don't bother folding single line directives
        if directive["lineno"] != directive["endline"]:
            results.append(
                {
                    "kind": "region",
                    "startLine": directive["lineno"],
                    "startCharacter": directive["start_char"],
                    "endLine": directive["endline"],
                    "endCharacter": directive["end_char"],
                }
            )

    return results
