from typing import List

from rst_lsp.docutils_ext.visitor import ElementType
from rst_lsp.server.constants import SymbolKind
from rst_lsp.server.datatypes import DocumentSymbol
from rst_lsp.server.workspace import Config, Document, Workspace
from rst_lsp.server.plugin_manager import hookimpl


@hookimpl
def rst_document_symbols(
    config: Config, workspace: Workspace, document: Document
) -> List[DocumentSymbol]:

    database = workspace.database
    uri = document.uri
    results = []
    results.extend(find_directives(None, uri, database))
    results.extend(find_roles(None, uri, database))
    results.extend(find_references(None, uri, database))

    for section in (
        database.query_elements(
            name=ElementType.section.value, uri=uri, section_uuid=None
        )
        or []
    ):
        title = section["title"]
        results.append(
            {
                "name": title,
                # "detail": "Some detail",
                "kind": SymbolKind.Module,
                "range": {
                    "start": {"line": section["lineno"], "character": 0},
                    "end": {"line": section["lineno"], "character": len(title) - 1},
                },
                "selectionRange": {
                    "start": {"line": section["lineno"], "character": 0},
                    "end": {"line": section["lineno"], "character": len(title) - 1},
                },
                "children": _create_children(section, uri, database),
            }
        )
    return results


def _create_children(section, uri, database):
    children = []
    children.extend(find_directives(section["uuid"], uri, database))
    children.extend(find_roles(section["uuid"], uri, database))
    children.extend(find_references(section["uuid"], uri, database))
    for sub_section in (
        database.query_elements(
            name=ElementType.section.value, uri=uri, section_uuid=section["uuid"]
        )
        or []
    ):
        title = sub_section["title"]
        children.append(
            {
                "name": title,
                # "detail": "Some detail",
                "kind": SymbolKind.Module,
                "range": {
                    "start": {"line": sub_section["lineno"], "character": 0},
                    "end": {"line": sub_section["lineno"], "character": len(title) - 1},
                },
                "selectionRange": {
                    "start": {"line": sub_section["lineno"], "character": 0},
                    "end": {"line": sub_section["lineno"], "character": len(title) - 1},
                },
                "children": _create_children(sub_section, uri, database),
            }
        )
    return children


def find_directives(section_uuid, uri, database):
    children = []
    for element in (
        database.query_elements(
            name=ElementType.directive.value, uri=uri, section_uuid=section_uuid,
        )
        or []
    ):
        children.append(
            {
                "name": element["type_name"],
                "kind": SymbolKind.Class,
                "range": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["endline"],
                        "character": element["end_char"],
                    },
                },
                "selectionRange": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["endline"],
                        "character": element["end_char"],
                    },
                },
            }
        )
    return children


def find_roles(section_uuid, uri, database):
    children = []
    for element in (
        database.query_elements(
            name=ElementType.role.value, uri=uri, section_uuid=section_uuid,
        )
        or []
    ):
        children.append(
            {
                "name": element["role"],
                "kind": SymbolKind.Function,
                "range": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["lineno"],
                        "character": element["end_char"],
                    },
                },
                "selectionRange": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["lineno"],
                        "character": element["end_char"],
                    },
                },
            }
        )
    return children


def find_references(section_uuid, uri, database):
    children = []
    for element in (
        database.query_elements(
            name=ElementType.reference.value, uri=uri, section_uuid=section_uuid,
        )
        or []
    ):
        children.append(
            {
                "name": f"ref:{element['ref_type']}",
                "kind": SymbolKind.Field,
                "range": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["lineno"],
                        "character": element["end_char"],
                    },
                },
                "selectionRange": {
                    "start": {
                        "line": element["lineno"],
                        "character": element["start_char"],
                    },
                    "end": {
                        "line": element["lineno"],
                        "character": element["end_char"],
                    },
                },
            }
        )
    return children
