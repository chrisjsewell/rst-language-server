import re

from rst_lsp.server.plugins import hookimpl
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.datatypes import Position
from rst_lsp.server.constants import CompletionItemKind

REGEX_ROLE_START = "role"


@hookimpl
def rst_completions(config: Config, workspace: Workspace, document: Document, position: Position):

    before = document.get_line_before(position)[::-1]  # reverse
    workspace.server.log_message(before)
    items = []
    if re.match("^[a-z]*:", before):
        items = [
            {
                "label": r["name"],
                "insertText": f"{r['name']}:`$0`",  # TODO replace with textEdit
                "kind": CompletionItemKind.Function,
                "detail": f"Module: {r['module']}",
                "documentation": r["description"],
                "insertTextFormat": 2,
            }
            for r in workspace.database.query_roles()
        ]
    if re.match(r"^\.\.", before):
        items = [
            {
                "label": d["name"],
                "insertText": f" {d['name']}:: $0",  # TODO replace with textEdit
                "kind": CompletionItemKind.Class,
                "detail": (
                    f"Class: {d['klass']}"
                    f"\nRequired Args: {d['required_arguments']}"
                    f"\nOptional Args: {d['optional_arguments']}"
                    f"\nHas Content: {d['has_content']}"
                ),
                "documentation": d["description"],
                "insertTextFormat": 2,
            }
            for d in workspace.database.query_directives()
        ]
    return items
