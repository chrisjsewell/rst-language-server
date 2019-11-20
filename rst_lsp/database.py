from inspect import getdoc  # , getmro

from tinydb import TinyDB, Query

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
    def __init__(self, path):
        self._db = TinyDB(path)
        self._query = Query()
        # FYI can also set query sizes for tables
        self._tbl_global = self._db.table("global")

    @property
    def db(self) -> TinyDB:
        return self._db

    @property
    def query(self) -> Query:
        return self._query

    @property
    def tbl_global(self):
        return self._tbl_global

    def update_classes(self, confdir=None, confoverrides=None):
        # TODO confdir, confoverrides should be stored in the dictionary separately
        query = self.query
        with init_sphinx(confdir=confdir, confoverrides=confoverrides) as sphinx_init:
            for name, role in sphinx_init.roles.items():
                self.tbl_global.upsert(
                    get_role_json(name, role),
                    (query.element == "role") & (query.name == name),
                )
            for name, directive in sphinx_init.directives.items():
                self.tbl_global.upsert(
                    get_directive_json(name, directive),
                    (query.element == "directive") & (query.name == name),
                )

    def query_role(self, name):
        return self.tbl_global.get(
            (self.query.element == "role") & (self.query.name == name)
        )

    def query_directive(self, name):
        return self.tbl_global.get(
            (self.query.element == "directive") & (self.query.name == name)
        )
