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
    results = database.query_elements(
        etype=("role", "directive"), uri=uri, startLine=position["line"],
    )
    logger.debug(results)
    for result in results or []:

        if result["startCharacter"] <= position["character"] and (
            result["endLine"] != position["line"]
            or position["character"] <= result["endCharacter"]
        ):
            if result["type"] == "role":
                role_data = database.query_role(result["rtype"])
                if role_data is None:
                    return {"contents": "Unknown role"}
                return {
                    "contents": [
                        {
                            "language": "yaml",
                            "value": (f"module: {role_data['module']}"),
                        },
                        {"language": "rst", "value": (f"{role_data['description']}")},
                    ]
                }
            else:
                dir_data = database.query_directive(result["dtype"])
                if dir_data is None:
                    return {"contents": "Unknown directive"}
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
    return {"contents": ""}
