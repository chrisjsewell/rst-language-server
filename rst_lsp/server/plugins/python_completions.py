import logging
from textwrap import dedent

from rst_lsp.docutils_ext.visitor import ElementType
from rst_lsp.server.plugin_manager import hookimpl
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.datatypes import Position
from rst_lsp.server.constants import CompletionItemKind

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
            name=ElementType.directive.value, uri=uri, type_name=["code", "code-block"]
        )
        or []
    )
    logger.debug(str(results))

    for result in results:
        if "python" not in result["arguments"]:
            continue
        if not ("start_char" in result and "end_char" in result):
            continue
        if not (
            result["start_char"] <= position["character"]
            and (
                result.get("endline", position["line"]) != position["line"]
                or position["character"] <= result["end_char"]
            )
        ):
            continue

        # find first line of source code
        lines = document.lines[result["lineno"] : result["endline"] + 1]
        start_line = None
        for i, line in enumerate(lines):
            if not line.strip():
                start_line = i + 1
                break
        if start_line is None or start_line >= len(lines):
            return []
        indent_spaces = len(lines[start_line]) - len(lines[start_line].lstrip())
        text = dedent("".join(lines[start_line:]))
        # TODO add warning message, if jedi not installed
        import jedi

        definitions = jedi.Script(
            source=text,
            line=position["line"] - result["lineno"] - start_line + 1,
            column=position["character"] - indent_spaces,
        ).completions()
        if not definitions:
            return None
        return [
            {
                "label": _label(d),
                "kind": _TYPE_MAP.get(d.type),
                "detail": _detail(d),
                "documentation": _format_docstring(d.docstring()),
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


def _format_docstring(contents):
    """Python doc strings come in a number of formats, but LSP wants markdown.

    Until we can find a fast enough way of discovering and parsing each format,
    we can do a little better by at least preserving indentation.
    """
    contents = contents.replace("\t", u"\u00A0" * 4)
    contents = contents.replace("  ", u"\u00A0" * 2)
    # if LooseVersion(JEDI_VERSION) < LooseVersion('0.15.0'):
    #     contents = contents.replace('*', '\\*')
    return contents
