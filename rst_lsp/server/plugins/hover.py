import logging

import yaml

from rst_lsp.server.datatypes import Position, Hover
from rst_lsp.server.workspace import Document
from rst_lsp.server.plugin_manager import hookimpl

logger = logging.getLogger(__name__)


@hookimpl
def rst_hover(document: Document, position: Position) -> Hover:

    database = document.workspace.database

    uri = document.uri
    result = database.query_at_position(
        uri=uri,
        line=position["line"],
        character=position["character"],
        filters_in={"category": ("role", "directive")},
        load_role=True,
        load_directive=True,
    )

    if result is None:
        return None

    if result.category == "role":
        if result.role is None:
            return {"contents": "Unknown role"}
        return {
            "contents": [
                {"language": "yaml", "value": (f"module: {result.role.module}")},
                {"language": "rst", "value": (f"{result.role.description}")},
            ]
        }
    elif result.startLine == position["line"]:
        if result.directive is None:
            return {"contents": "Unknown directive"}
        dir_data = result.directive.column_dict()
        options = yaml.safe_dump({"options": dir_data["options"]})
        return {
            "contents": [
                {
                    "language": "yaml",
                    "value": (
                        f"class: {dir_data['klass']}\n"
                        f"required arguments: {dir_data['required_arguments']}\n"
                        f"optional arguments: {dir_data['optional_arguments']}\n"
                        f"has_content: {dir_data['has_content']}\n"
                        f"{options}"
                    ),
                },
                {"language": "rst", "value": f"{dir_data['description']}"},
            ]
        }
    return None
