from rst_lsp.database.tinydb import Database
from rst_lsp.docutils_ext.visitor import ElementType


def foldingRange(uri: str, database: Database):
    """Return folding ranges for a document.

    See:
    https://microsoft.github.io/language-server-protocol/specifications/specification-3-14/#textDocument_foldingRange
    """
    results = []
    document = database.query_doc(uri)

    # TODO probably want startCharacter to be at the end of the startLine?

    # Get section folding
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
                        "endLine": section["lineno"],
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
                "endLine": document["endline"],
                "endCharacter": document["endchar"],
            }
        )

    # Get directive folding
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
