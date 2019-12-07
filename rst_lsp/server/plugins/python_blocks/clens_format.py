from textwrap import dedent, indent
from typing import Any, List, Optional

from rst_lsp.server.datatypes import CodeLens, WorkspaceEdit
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.plugin_manager import hookimpl

COMMAND_NAME = "rst_format_python_cell"


@hookimpl
def rst_code_lens(
    config: Config, workspace: Workspace, document: Document
) -> List[CodeLens]:

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
    edits = []
    for result in results:
        edits.append(
            {
                "range": {
                    "start": {
                        "line": result["startLine"],
                        "character": result["startCharacter"],
                    },
                    "end": {
                        "line": result["startLine"],
                        "character": result["startCharacter"],
                    },
                },
                "command": {
                    "title": "format",
                    "command": COMMAND_NAME,
                    "arguments": [
                        uri,
                        result,
                        document.lines[result["startLine"] : result["endLine"] + 1],
                    ],
                },
            }
        )

    return edits


@hookimpl
def rst_commands(config: Config, workspace: Workspace):
    return [COMMAND_NAME]


@hookimpl
def rst_execute_command(
    config: Config, workspace: Workspace, command: str, arguments: Optional[List[Any]],
) -> WorkspaceEdit:
    if command != COMMAND_NAME:
        return None
    # TODO add warning message, if black not installed
    import black

    uri, result, lines = arguments

    # find first line of source code
    start_line = None
    for i, line in enumerate(lines):
        if not line.strip():
            start_line = i + 1
            break
    if start_line is None or start_line >= len(lines):
        return {"changes": {}}

    indent_spaces = len(lines[start_line]) - len(lines[start_line].lstrip())
    text = dedent("".join(lines[start_line:]))
    # TODO add warning message, if black formatting fails
    text = black.format_str(text, mode=black.FileMode()).rstrip()

    return {
        "changes": {
            uri: [
                {
                    "range": {
                        "start": {
                            "line": result["startLine"] + start_line,
                            "character": 0,
                        },
                        "end": {"line": result["endLine"], "character": len(lines[-1])},
                    },
                    "newText": indent(text, indent_spaces * " "),
                }
            ]
        }
    }
