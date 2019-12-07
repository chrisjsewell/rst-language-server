import logging

from rst_lsp.server.datatypes import Position, Hover
from rst_lsp.server.workspace import Document
from rst_lsp.server.plugin_manager import hookimpl

from .utils import format_docstring

logger = logging.getLogger(__name__)


@hookimpl
def rst_hover(document: Document, position: Position) -> Hover:

    database = document.workspace.database
    uri = document.uri

    results = (
        database.query_elements(
            etype="directive",
            uri=uri,
            dtype=("code", "code-block"),
            arguments=["python"],
        )
        or []
    )

    for result in results:
        if not (
            position["line"] >= result["contentLine"]
            and position["line"] <= result["endLine"]
            and position["character"] >= result["contentIndent"]
        ):
            continue

        lines = document.lines[result["contentLine"] : result["endLine"] + 1]
        text = "\n".join([l[result["contentIndent"] :].rstrip() for l in lines])
        # TODO add warning message, if jedi not installed
        import jedi

        definitions = jedi.Script(
            source=text,
            line=position["line"] - result["contentLine"] + 1,
            column=position["character"] - result["contentIndent"],
        ).goto_definitions()

        word = document.word_at_position(position)

        # Find first exact matching definition
        definition = next((x for x in definitions if x.name == word), None)

        if not definition:
            return {"contents": ""}

        # raw docstring returns only doc, without signature
        doc = format_docstring(definition.docstring(raw=True))

        # Find first exact matching signature
        signature = next(
            (x.to_string() for x in definition.get_signatures() if x.name == word), ""
        )

        contents = []
        if signature:
            contents.append({"language": "python", "value": signature})
        if doc:
            contents.append(doc)
        if not contents:
            return {"contents": ""}
        return {"contents": contents}
