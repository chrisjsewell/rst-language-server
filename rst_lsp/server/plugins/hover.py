import yaml

from rst_lsp.docutils_ext.visitor import ElementType
from rst_lsp.server.datatypes import Position, Hover
from rst_lsp.server.workspace import Document
from rst_lsp.server.plugin_manager import hookimpl


@hookimpl
def rst_hover(document: Document, position: Position) -> Hover:

    database = document.workspace.database
    uri = document.uri
    results = database.query_elements(
        name=[ElementType.role.value, ElementType.directive.value],
        uri=uri,
        lineno=position["line"],
    )
    # document.workspace.server.log_message(str(results))
    for result in results or []:
        if not ("start_char" in result and "end_char" in result):
            continue

        if result["start_char"] <= position["character"] and (
            result.get("endline", position["line"]) != position["line"]
            or position["character"] <= result["end_char"]
        ):
            if result["element"] == ElementType.role.value:
                role_data = database.query_role(result["role"])
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
                dir_data = database.query_directive(result["type_name"])
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
