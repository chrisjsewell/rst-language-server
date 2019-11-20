from inspect import getdoc  # , getmro

from tinydb import TinyDB, Query
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage

from .parser import init_sphinx


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
        self._tbl_global = self._db.table("global")
        self._tbl_docs = self._db.table("docs")
        self._tbl_linting = self._db.table("linting")

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
    def tbl_docs(self):
        return self._tbl_docs

    def update_classes(self, confdir=None, confoverrides=None):
        # TODO confdir, confoverrides should be stored in the dictionary separately
        with init_sphinx(confdir=confdir, confoverrides=confoverrides) as sphinx_init:
            for name, role in sphinx_init.roles.items():
                self.tbl_global.upsert(
                    get_role_json(name, role),
                    (self.query.element == "role") & (self.query.name == name),
                )
            for name, directive in sphinx_init.directives.items():
                self.tbl_global.upsert(
                    get_directive_json(name, directive),
                    (self.query.element == "directive") & (self.query.name == name),
                )

    def query_role(self, name):
        return self.tbl_global.get(
            (self.query.element == "role") & (self.query.name == name)
        )

    def query_directive(self, name):
        return self.tbl_global.get(
            (self.query.element == "directive") & (self.query.name == name)
        )

    def update_doc_lint(self, doc_name, errors):
        pass
