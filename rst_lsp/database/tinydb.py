"""TinyDB implementation of a backend database."""
from datetime import datetime
import logging
import threading
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

logger = logging.getLogger(__name__)


class NotSet:
    pass


def synchronized(method):
    """Thread lock a method."""

    def new_method(self, *arg, **kws):
        with self.thread_lock:
            return method(self, *arg, **kws)

    return new_method


# TODO make abstract base class
class SynchronizedDatabase:
    def __init__(self, path=None, in_memory=False, cache_writes=False):
        """A database for storing language-server data.

        All ``update_`` and ``query__`` methods are thread locked,
        to avoid any issues with concurrent read/write operations.

        Also you can use as a context manager,
        which will thread lock for the duration::

            db = SynchronizedDatabase()
            with db:
                db.update_ ...
                db.query_ ...


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
        if path is None:
            self._db = TinyDB(storage=MemoryStorage,)
        else:
            self._db = TinyDB(
                path,
                storage=CachingMiddleware(JSONStorage) if cache_writes else JSONStorage,
            )
        self._path = path
        self.thread_lock = threading.RLock()

        # define tables
        # FYI can also set query sizes for tables

        # TODO configuration table
        # stores information about all roles and directives available
        self._tbl_classes = self._db.table("classes")  # type: Table
        # stores information related to loaded documents,
        # e.g. their uri and last time they were updated
        self._tbl_documents = self._db.table("documents")  # type: Table
        # stores information about the elements contained in each document
        self._tbl_positions = self._db.table("positions")  # type: Table
        # stores information references and targets,
        # linking back to uuids in the positions table
        self._tbl_references = self._db.table("references")  # type: Table
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

    def __enter__(self):
        self.thread_lock.acquire()
        self._db.__enter__()
        return self

    def __exit__(self, *args):
        self._db.__exit__(*args)
        self.thread_lock.release()

    # @property
    # def db(self) -> TinyDB:
    #     return self._db

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

    @synchronized
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

    @synchronized
    def query_conf_file(self):
        return self._tbl_documents.get(where("dtype") == "configuration")

    @synchronized
    def query_role(self, name: str) -> RoleInfo:
        return self._tbl_classes.get(
            (where("element") == "role") & (where("name") == name)
        )

    @synchronized
    def query_roles(self, names: list = None) -> List[RoleInfo]:
        if names is None:
            return self._tbl_classes.search(where("element") == "role")
        return self._tbl_classes.search(
            (where("element") == "role") & (where("name").one_of(names))
        )

    @synchronized
    def query_directive(self, name: str) -> DirectiveInfo:
        return self._tbl_classes.get(
            (where("element") == "directive") & (where("name") == name)
        )

    @synchronized
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

    def _update_doc_positions(self, uri: str, positions: List[dict]):
        self._tbl_positions.remove(where("uri") == uri)
        db_docs = []
        for element in positions:
            doc = {"uri": uri}
            doc.update(element)
            db_docs.append(doc)
        self._tbl_positions.insert_multiple(db_docs)

    def _update_doc_references(self, uri: str, references: List[dict]):
        self._tbl_references.remove(where("uri") == uri)
        db_docs = []
        for element in references:
            doc = {"uri": uri}
            doc.update(element)
            db_docs.append(doc)
        self._tbl_references.insert_multiple(db_docs)

    def _update_doc_symbols(self, uri: str, doc_symbols: List[dict]):
        self._tbl_doc_symbols.remove(where("uri") == uri)
        self._tbl_doc_symbols.insert({"uri": uri, "doc_symbols": doc_symbols})

    @synchronized
    def update_doc(
        self,
        uri: str,
        positions: List[dict],
        references: List[dict],
        doc_symbols: List[dict],
        lints: List[dict],
    ):
        self._tbl_documents.upsert(
            {"dtype": "rst", "uri": uri, "modified": self.get_current_time()},
            (where("dtype") == "rst") & (where("uri") == uri),
        )
        self._update_doc_positions(uri, positions)
        self._update_doc_references(uri, references)
        self._update_doc_symbols(uri, doc_symbols)
        self._update_doc_lint(uri, lints)

    @synchronized
    def query_doc(self, uri):
        return self._tbl_documents.get(
            (where("dtype") == "rst") & (where("uri") == uri)
        )

    @synchronized
    def query_docs(self, uris: list = None):
        if uris is None:
            return self._tbl_documents.search(where("dtype") == "rst")
        return self._tbl_documents.search(
            (where("dtype") == "rst") & (where("uri").one_of(uris))
        )

    @synchronized
    def query_lint(self, uri: str):
        return self._tbl_linting.search(where("uri") == uri)

    @synchronized
    def query_doc_symbols(self, uri: str):
        doc_symbols = self._tbl_doc_symbols.get(where("uri") == uri)
        if doc_symbols is not None:
            return doc_symbols["doc_symbols"]

    @synchronized
    def query_position_uuid(self, uuid: str):
        return self._tbl_positions.get(where("uuid") == uuid)

    @synchronized
    def query_at_position(self, uri: str, line: int, character: int, **kwargs):
        query = where("uri") == uri
        for key, value in kwargs.items():
            if isinstance(value, tuple):
                query = (query) & (where(key).one_of(value))
            else:
                query = (query) & (where(key) == value)
        query = (query) & (where("startLine") <= line) & (where("endLine") >= line)
        # find the result that has the smallest line range
        # TODO also smallest character range?
        final_result = None
        final_line_range = None
        for result in self._tbl_positions.search(query) or []:
            if line == result["startLine"] and character < result["startCharacter"]:
                continue
            if line == result["endLine"] and character > result["endCharacter"]:
                continue
            line_range = result["endLine"] - result["startLine"]
            if final_result is None:
                final_line_range = line_range
                final_result = result
                continue
            if line_range < final_line_range:
                final_line_range = line_range
                final_result = result
        return final_result

    @synchronized
    def query_positions(
        self,
        *,
        uri: Optional[Union[str, tuple]] = NotSet(),
        block: Optional[bool] = NotSet(),
        etype: Optional[Union[str, tuple]] = NotSet(),
        parent_uuid: Optional[Union[str, tuple]] = NotSet(),
        uuid: Optional[Union[str, tuple]] = NotSet(),
        **kwargs
    ):
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
            return self._tbl_positions.all()
        return self._tbl_positions.search(query)

    @synchronized
    def query_references(self, uri: str, position_uuid: str):
        query = (where("uri") == uri) & (where("position_uuid") == position_uuid)
        results = self._tbl_references.search(query) or []
        all_results = []
        for result in results:
            if result.get("target", None) or result.get("reference", None):
                all_results.append(result)
            if result.get("target", None):
                query = (
                    (where("uri") == uri)
                    & (where("position_uuid") != position_uuid)
                    & (where("reference") == result["target"])
                )
                all_results.extend(self._tbl_references.search(query) or [])
            if result.get("reference", None):
                query = (
                    (where("uri") == uri)
                    & (where("position_uuid") != position_uuid)
                    & (where("target") == result["reference"])
                )
                all_results.extend(self._tbl_references.search(query) or [])
                query = (
                    (where("uri") == uri)
                    & (where("position_uuid") != position_uuid)
                    & (where("reference") == result["reference"])
                )
                all_results.extend(self._tbl_references.search(query) or [])
        return all_results

    @synchronized
    def query_definitions(self, uri: str, position_uuid: str):
        query = (where("uri") == uri) & (where("position_uuid") == position_uuid)
        results = self._tbl_references.search(query) or []
        all_results = []
        for result in results:
            if result.get("reference", None):
                query = (where("uri") == uri) & (where("target") == result["reference"])
                all_results.extend(self._tbl_references.search(query) or [])
        return all_results
