"""TinyDB implementation of a backend database."""
from datetime import datetime
from typing import List, Optional, Union

from tinydb import TinyDB, where
from tinydb.database import Table
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage, MemoryStorage


from rst_lsp.database.utils import (
    RoleInfo,
    DirectiveInfo,
    get_role_json,
    get_directive_json,
)


class NotSet:
    pass


# TODO make abstract base class
class Database:
    def __init__(self, path=None, in_memory=False, cache_writes=False):
        """A database for storing language-server data.

        Parameters
        ----------
        path : str
            path for the database file
        in_memory: bool
            whether the database is stored or not
        cache_writes : bool
            caches all read operations and writes data to disk,
            only after a configured number of write operations.
            WARNING this should only be used with a context manager.
            (see https://tinydb.readthedocs.io/en/latest/usage.html#cachingmiddleware)

        """
        if in_memory:
            self._db = TinyDB(storage=MemoryStorage,)
        else:
            self._db = TinyDB(
                path,
                storage=CachingMiddleware(JSONStorage) if cache_writes else JSONStorage,
            )
        self._path = path

        # define tables
        # FYI can also set query sizes for tables

        # TODO configuration table
        # stores information about all roles and directives available
        self._tbl_classes = self._db.table("classes")  # type: Table
        # stores information related to loaded documents,
        # e.g. their uri and last time they were updated
        self._tbl_documents = self._db.table("documents")  # type: Table
        # stores information about the elements contained in each document
        self._tbl_elements = self._db.table("elements")  # type: Table
        # stores the document symbols nested mapping for each document
        # TODO is there a better way to store this?
        self._tbl_doc_symbols = self._db.table("doc_symbols")  # type: Table
        # stores information about linting errors/warnings in each document
        self._tbl_linting = self._db.table("linting")  # type: Table

    def close(self):
        """Close the database."""
        self._db.close()

    @property
    def path(self) -> str:
        return self._path

    @property
    def db(self) -> TinyDB:
        return self._db

    @staticmethod
    def get_current_time():
        return datetime.utcnow().isoformat()

    def _update_classes(self, roles: dict, directives: dict):
        self._tbl_classes.remove(where("element") == "role")
        self._tbl_classes.insert_multiple(
            [get_role_json(name, role) for name, role in roles.items()],
        )
        self._tbl_classes.remove(where("element") == "directive")
        self._tbl_classes.insert_multiple(
            [
                get_directive_json(name, directive)
                for name, directive in directives.items()
            ],
        )

    def update_conf_file(self, uri: Optional[str], roles: dict, directives: dict):
        # only one configuration file is allowed
        self._tbl_documents.remove(where("dtype") == "configuration")
        if uri is not None:
            self._tbl_documents.insert(
                {
                    "dtype": "configuration",
                    "uri": uri,
                    "modified": self.get_current_time(),
                },
            )
        self._update_classes(roles, directives)

    def query_conf_file(self):
        return self._tbl_documents.get(where("dtype") == "configuration")

    def query_role(self, name: str) -> RoleInfo:
        return self._tbl_classes.get(
            (where("element") == "role") & (where("name") == name)
        )

    def query_roles(self, names: list = None) -> List[RoleInfo]:
        if names is None:
            return self._tbl_classes.search(where("element") == "role")
        return self._tbl_classes.search(
            (where("element") == "role") & (where("name").one_of(names))
        )

    def query_directive(self, name: str) -> DirectiveInfo:
        return self._tbl_classes.get(
            (where("element") == "directive") & (where("name") == name)
        )

    def query_directives(self, names: list = None) -> List[DirectiveInfo]:
        if names is None:
            return self._tbl_classes.search(where("element") == "directive")
        return self._tbl_classes.search(
            (where("element") == "directive") & (where("name").one_of(names))
        )

    def _update_doc_lint(self, uri: str, lints: List[dict]):
        self._tbl_linting.remove(where("uri") == uri)
        db_docs = []
        for lint in lints:
            doc = {"uri": uri}
            doc.update(lint)
            db_docs.append(doc)
        self._tbl_linting.insert_multiple(db_docs)

    def _update_doc_elements(self, uri: str, elements: List[dict]):
        self._tbl_elements.remove(where("uri") == uri)
        db_docs = []
        for element in elements:
            doc = {"uri": uri}
            doc.update(element)
            db_docs.append(doc)
        self._tbl_elements.insert_multiple(db_docs)

    def _update_doc_symbols(self, uri: str, doc_symbols: List[dict]):
        self._tbl_doc_symbols.remove(where("uri") == uri)
        self._tbl_doc_symbols.insert({"uri": uri, "doc_symbols": doc_symbols})

    def update_doc(
        self,
        uri: str,
        elements: List[dict],
        doc_symbols: List[dict],
        lints: List[dict],
    ):
        self._tbl_documents.upsert(
            {"dtype": "rst", "uri": uri, "modified": self.get_current_time()},
            (where("dtype") == "rst") & (where("uri") == uri),
        )
        self._update_doc_elements(uri, elements)
        self._update_doc_symbols(uri, doc_symbols)
        self._update_doc_lint(uri, lints)

    def query_doc(self, uri):
        return self._tbl_documents.get(
            (where("dtype") == "rst") & (where("uri") == uri)
        )

    def query_docs(self, uris: list = None):
        if uris is None:
            return self._tbl_documents.search(where("dtype") == "rst")
        return self._tbl_documents.search(
            (where("dtype") == "rst") & (where("uri").one_of(uris))
        )

    def query_lint(self, uri: str):
        return self._tbl_linting.search(where("uri") == uri)

    def query_doc_symbols(self, uri: str):
        doc_symbols = self._tbl_doc_symbols.get(where("uri") == uri)
        if doc_symbols is not None:
            return doc_symbols["doc_symbols"]

    def query_elements(
        self,
        *,
        uri: Optional[Union[str, tuple]] = NotSet(),
        block: Optional[bool] = NotSet(),
        etype: Optional[Union[str, tuple]] = NotSet(),
        parent_uuid: Optional[Union[str, tuple]] = NotSet(),
        uuid: Optional[Union[str, tuple]] = NotSet(),
        has_keys: List[str] = (),
        **kwargs
        # TODO it would be ideal if uuid and database.table.doc_id were the same thing
        # TODO match within range
    ):
        if has_keys:
            query = where(has_keys[0]).exists()
            for key in has_keys[1:]:
                query = (query) & (where(key).exists())
        else:
            query = None
        for value, key in [
            (uri, "uri"),
            (etype, "type"),
            (block, "block"),
            (parent_uuid, "parent_uuid"),
            (uuid, "uuid"),
        ] + [(v, k) for k, v in kwargs.items()]:
            if isinstance(value, NotSet):
                continue
            if isinstance(value, tuple):
                key_query = where(key).one_of(value)
            else:
                key_query = where(key) == value
            if query is None:
                query = key_query
            else:
                query = (query) & (key_query)

        if query is None:
            return self._tbl_elements.all()
        return self._tbl_elements.search(query)

    def query_targets(
        self, uri: str, refs_samedoc: List[str], *, target_key="targets",
    ):
        def contains_ref(targets):
            return True if set(targets).intersection(refs_samedoc) else False

        query = (where("uri") == uri) & (where(target_key).test(contains_ref))
        return self._tbl_elements.search(query)
