from inspect import getdoc  # , getmro
from typing import List

import attr

from tinydb import TinyDB, Query
from tinydb.database import Table
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage


def get_role_json(name, role):
    return {
        "element": "role",
        "name": name,
        "description": getdoc(role) or "",
        "module": f"{role.__module__}",
    }


def get_directive_json(name, direct):
    data = {
        "element": "directive",
        "name": name,
        "description": getdoc(direct) or "",
        "class": f"{direct.__module__}.{direct.__name__}",
        "required_arguments": direct.required_arguments,
        "optional_arguments": direct.optional_arguments,
        "has_content": direct.has_content,
        "options": {k: str(v.__name__) for k, v in direct.option_spec.items()}
        if direct.option_spec
        else {},
    }
    return data


def get_element_json(block_objects: list, inline_objects: list):
    objs = []
    for obj in block_objects:
        dct = attr.asdict(obj)
        dct.pop("parent", None)  # this is a docutils.doctree element
        dct["type"] = "Block"
        dct["element"] = obj.__class__.__name__
        objs.append(dct)
    objs.extend(inline_objects)
    return objs


class Database:
    def __init__(self, path, cache_writes=True):
        # caches all read operations and writes data to disk,
        # after a configured number of write operations
        # TODO the database has a ``close``` method that should be called,
        # to store any cached writes, before shutting down the server.
        self._db = TinyDB(
            path,
            storage=CachingMiddleware(JSONStorage) if cache_writes else JSONStorage,
        )
        self._query = Query()
        # FYI can also set query sizes for tables
        self._tbl_global = self._db.table("global")  # type: Table
        self._tbl_elements = self._db.table("elements")  # type: Table
        self._tbl_linting = self._db.table("linting")  # type: Table

    @property
    def db(self) -> TinyDB:
        return self._db

    @property
    def query(self) -> Query:
        return self._query

    @property
    def tbl_global(self):
        return self._tbl_global

    @property
    def tbl_linting(self):
        return self._tbl_linting

    @property
    def tbl_elements(self):
        return self._tbl_elements

    def update_classes(self, roles: dict, directives: dict):
        self.tbl_global.remove(self.query.element == "role")
        for name, role in roles.items():
            self.tbl_global.upsert(
                get_role_json(name, role),
                (self.query.element == "role") & (self.query.name == name),
            )
        self.tbl_global.remove(self.query.element == "directive")
        for name, directive in directives.items():
            self.tbl_global.upsert(
                get_directive_json(name, directive),
                (self.query.element == "directive") & (self.query.name == name),
            )

    def query_role(self, name: str):
        return self.tbl_global.get(
            (self.query.element == "role") & (self.query.name == name)
        )

    def query_directive(self, name: str):
        return self.tbl_global.get(
            (self.query.element == "directive") & (self.query.name == name)
        )

    def update_doc_lint(self, doc_path: str, errors: List[dict]):
        self.tbl_linting.remove(self.query.doc_path == doc_path)
        for error in errors:
            doc = {"doc_path": doc_path}
            doc.update(error)
            self.tbl_linting.insert(doc)

    def update_doc_elements(self, doc_path: str, elements: List[dict]):
        self.tbl_elements.remove(self.query.doc_path == doc_path)
        for element in elements:
            doc = {"doc_path": doc_path}
            doc.update(element)
            self.tbl_elements.insert(doc)
