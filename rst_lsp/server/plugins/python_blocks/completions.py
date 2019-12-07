import logging

from rst_lsp.server.plugin_manager import hookimpl
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.datatypes import Position
from rst_lsp.server.constants import CompletionItemKind

from .utils import format_docstring

logger = logging.getLogger(__name__)

# Map to the VSCode type
_TYPE_MAP = {
    "none": CompletionItemKind.Value,
    "type": CompletionItemKind.Class,
    "tuple": CompletionItemKind.Class,
    "dict": CompletionItemKind.Class,
    "dictionary": CompletionItemKind.Class,
    "function": CompletionItemKind.Function,
    "lambda": CompletionItemKind.Function,
    "generator": CompletionItemKind.Function,
    "class": CompletionItemKind.Class,
    "instance": CompletionItemKind.Reference,
    "method": CompletionItemKind.Method,
    "builtin": CompletionItemKind.Class,
    "builtinfunction": CompletionItemKind.Function,
    "module": CompletionItemKind.Module,
    "file": CompletionItemKind.File,
    "xrange": CompletionItemKind.Class,
    "slice": CompletionItemKind.Class,
    "traceback": CompletionItemKind.Class,
    "frame": CompletionItemKind.Class,
    "buffer": CompletionItemKind.Class,
    "dictproxy": CompletionItemKind.Class,
    "funcdef": CompletionItemKind.Function,
    "property": CompletionItemKind.Property,
    "import": CompletionItemKind.Module,
    "keyword": CompletionItemKind.Keyword,
    "constant": CompletionItemKind.Variable,
    "variable": CompletionItemKind.Variable,
    "value": CompletionItemKind.Value,
    "param": CompletionItemKind.Variable,
    "statement": CompletionItemKind.Keyword,
}


@hookimpl
def rst_completions(
    config: Config, workspace: Workspace, document: Document, position: Position
):
    logger.debug("called python completions")
    database = workspace.database
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
        text = "".join([l[result["contentIndent"] :] for l in lines])
        # TODO add warning message, if jedi not installed
        import jedi

        definitions = jedi.Script(
            source=text,
            line=position["line"] - result["contentLine"] + 1,
            column=position["character"] - result["contentIndent"],
        ).completions()
        if not definitions:
            return None
        return [
            {
                "label": _label(d),
                "kind": _TYPE_MAP.get(d.type),
                "detail": _detail(d),
                "documentation": format_docstring(d.docstring()),
                "sortText": _sort_text(d),
                "insertText": d.name,
            }
            for d in definitions
        ] or None

    return None


def _label(definition):
    if definition.type in ("function", "method") and hasattr(definition, "params"):
        params = ", ".join([param.name for param in definition.params])
        return "{}({})".format(definition.name, params)

    return definition.name


def _detail(definition):
    try:
        return definition.parent().full_name or ""
    except AttributeError:
        return definition.full_name or ""


def _sort_text(definition):
    """ Ensure builtins appear at the bottom.
    Description is of format <type>: <module>.<item>
    """

    # If its 'hidden', put it next last
    prefix = "z{}" if definition.name.startswith("_") else "a{}"
    return prefix.format(definition.name)
