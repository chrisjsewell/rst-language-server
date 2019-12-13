"""SQLITE implementation of a backend database."""
from collections import defaultdict
import json
import sqlite3
from typing import Iterable, List, Optional, Union

from rst_lsp.database.utils import (
    RoleInfo,
    DirectiveInfo,
    get_role_json,
    get_directive_json,
)


class NotSet:
    pass


def bool_to_int(value):
    if isinstance(value, bool):
        return 1 if value else 0
    return value


class Database:
    def __init__(self, path=None):
        self._path = path
        self._connection = None
        self._tbl_columns = {}
        # TODO split self.open from init
        self.open()

    @property
    def path(self) -> str:
        return self._path

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("connection is closed call open() first")
        return self._connection

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def open(self):
        self._connection = sqlite3.connect(self.path if self.path else ":memory:")
        self._connection.row_factory = sqlite3.Row
        self._create_tables()

    def close(self):
        """Close the database."""
        self._connection.close()
        self._connection = None

    def _create_tables(self):
        with self.connection:
            cursor = self.cursor
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS roles ("
                "name text PRIMARY KEY, element text, description text, module text"
                ")"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS directives ("
                "name text PRIMARY KEY, element text, description text, klass text, "
                "required_arguments int, optional_arguments int, has_content int, "
                "options text"
                ")"
            )
            # TODO has_content is now an int not bool,
            # and options is text (from json.dumps)
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS documents ("
                "uri text PRIMARY KEY, dtype text, mtime text"
                ")"
            )
            # TODO changed modified to mtime
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS positions ("
                "uuid str PRIMARY KEY, "
                "uri text, "
                # TODO can FOREIGN KEY be None?
                "parent_uuid text, "
                # TODO block is now an int not bool
                "block int, type text, title text, "
                "startLine int, startCharacter int, endLine int, endCharacter int, "
                # TODO move type specific data to separate tables?
                # sections
                "level int, "
                # interpreted
                "rtype text, "
                # directives
                "dtype text, contentLine int, contentIndent int, klass text, "
                # TODO arguments and options now bytes
                "arguments bytes, options bytes, "
                "FOREIGN KEY (uri) REFERENCES documents (uri), "
                "FOREIGN KEY (parent_uuid) REFERENCES positions (uuid)"
                ")"
            )
            # TODO split references table into referencing and targets
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS referencing ("
                "reference text, "
                "uri text, "
                "position_uuid text, "
                # TODO storing classes as bytes, and same_doc int not bool
                "node text, same_doc int, classes bytes, "
                "FOREIGN KEY (position_uuid) REFERENCES positions (uuid)"
                ")"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS targets ("
                "target text, "
                "uri text, "
                "position_uuid text, "
                # TODO storing classes as bytes, and same_doc int not bool
                "node text, same_doc int, classes bytes, "
                "FOREIGN KEY (position_uuid) REFERENCES positions (uuid)"
                ")"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS doc_symbols ("
                "uri text PRIMARY KEY, "
                # TODO storing whole blob as text, using json.dumps
                "data text, "
                "FOREIGN KEY (uri) REFERENCES documents (uri)"
                ")"
            )
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS linting ("
                "uri text, "
                "source text, line int, type text, level int, description text, "
                "FOREIGN KEY (uri) REFERENCES documents (uri)"
                ")"
            )

        # collect the column names for each table
        self._tbl_columns = {}
        for table in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall():
            cursor.execute(f'SELECT * FROM {table["name"]}')
            self._tbl_columns[table["name"]] = [d[0] for d in cursor.description]

    def to_json(self) -> dict:
        """For testing."""
        cursor = self.cursor
        return {
            table: [
                dict(r) for r in cursor.execute(f"SELECT * FROM {table}").fetchall()
            ]
            for table in self._tbl_columns
        }

    def get_values_string(self, table_name: str) -> str:
        return "(" + ",".join(f":{c}" for c in self._tbl_columns[table_name]) + ")"

    def update_conf_file(self, uri: Optional[str], roles: dict, directives: dict):
        # TODO pass mtime
        with self.connection:
            cursor = self.cursor
            cursor.execute("DELETE FROM documents WHERE dtype='configuration'")
            cursor.execute(
                f"REPLACE INTO documents VALUES {self.get_values_string('documents')}",
                {"dtype": "configuration", "uri": uri, "mtime": None},
            )
            cursor.execute("DELETE FROM roles")
            cursor.executemany(
                f"REPLACE INTO roles VALUES {self.get_values_string('roles')}",
                [get_role_json(name, role) for name, role in roles.items()],
            )
            cursor.execute("DELETE FROM directives")
            cursor.executemany(
                f"REPLACE INTO directives VALUES {self.get_values_string('directives')}",
                [
                    get_directive_json(name, directive)
                    for name, directive in directives.items()
                ],
            )

    def query_conf_file(self) -> dict:
        result = self.cursor.execute(
            "SELECT * FROM documents WHERE dtype=?", ("configuration",)
        ).fetchone()
        return None if result is None else dict(result)

    def query_role(self, name: str) -> RoleInfo:
        result = self.cursor.execute(
            "SELECT * FROM roles WHERE name=?", (name,)
        ).fetchone()
        return None if result is None else dict(result)

    def query_roles(self, names: list = None) -> Iterable[RoleInfo]:
        if names is not None:
            results = self.cursor.execute(
                f"SELECT * FROM roles WHERE name IN ({','.join('?' for _ in names)})",
                names,
            ).fetchall()
        else:
            results = self.cursor.execute("SELECT * FROM roles",).fetchall()
        for result in results:
            yield dict(result)

    def query_directive(self, name: str) -> DirectiveInfo:
        result = self.cursor.execute(
            "SELECT * FROM directives WHERE name=?", (name,)
        ).fetchone()
        if result is not None:
            result = dict(result)
            result["has_content"] = True if result["has_content"] else False
            result["options"] = json.loads(result["options"])
        return result

    def query_directives(self, names: list = None) -> Iterable[DirectiveInfo]:
        if names is not None:
            results = self.cursor.execute(
                (
                    "SELECT * FROM directives WHERE name IN "
                    f"({','.join('?' for _ in names)})"
                ),
                names,
            ).fetchall()
        else:
            results = self.cursor.execute("SELECT * FROM directives",).fetchall()
        for result in results:
            result = dict(result)
            result["has_content"] = True if result["has_content"] else False
            result["options"] = json.loads(result["options"])
            yield result

    @staticmethod
    def _add_uri_to_dicts(dicts, uri, use_default=False):
        doc_dicts = []
        for element in dicts:
            doc = {"uri": uri}
            doc.update(element)
            if use_default:
                doc = defaultdict(lambda: None, doc)
            doc_dicts.append(doc)
        return doc_dicts

    def update_doc(
        self,
        uri: str,
        positions: List[dict],
        references: List[dict],
        doc_symbols: List[dict],
        lints: List[dict],
    ):
        # TODO pass mtime
        with self.connection:
            cursor = self.cursor
            cursor.execute(
                f"REPLACE INTO documents VALUES {self.get_values_string('documents')}",
                {"dtype": "rst", "uri": uri, "mtime": None},
            )
            cursor.execute(
                (
                    "REPLACE INTO doc_symbols VALUES "
                    f"{self.get_values_string('doc_symbols')}"
                ),
                {"uri": uri, "data": json.dumps(doc_symbols)},
            )
            cursor.execute("DELETE FROM positions WHERE uri=?", (uri,))
            cursor.execute("DELETE FROM linting WHERE uri=?", (uri,))
            cursor.execute("DELETE FROM referencing WHERE uri=?", (uri,))
            cursor.execute("DELETE FROM targets WHERE uri=?", (uri,))
            cursor.executemany(
                f"INSERT INTO positions VALUES {self.get_values_string('positions')}",
                self._add_uri_to_dicts(positions, uri, use_default=True),
            )
            cursor.executemany(
                f"INSERT INTO linting VALUES {self.get_values_string('linting')}",
                self._add_uri_to_dicts(lints, uri),
            )
            # TODO referencing and targets

    def query_doc(self, uri: str) -> dict:
        result = self.cursor.execute(
            "SELECT * FROM documents WHERE dtype=? AND uri=?", ("rst", uri)
        ).fetchone()
        return None if result is None else dict(result)

    def query_docs(self, uris: list = None) -> Iterable[dict]:
        if uris is not None:
            results = self.cursor.execute(
                f"SELECT * FROM documents WHERE name IN ({','.join('?' for _ in uris)})",
                uris,
            ).fetchall()
        else:
            results = self.cursor.execute("SELECT * FROM documents").fetchall()
        for result in results:
            yield dict(result)

    def query_lint(self, uri: str) -> Iterable[dict]:
        results = self.cursor.execute(
            f"SELECT * FROM linting WHERE uri=?", (uri,),
        ).fetchall()
        for result in results:
            yield dict(result)

    def query_doc_symbols(self, uri: str) -> Optional[List[dict]]:
        result = self.cursor.execute(
            "SELECT * FROM doc_symbols WHERE uri=?", (uri,)
        ).fetchone()
        if result is not None:
            result = json.loads(result["data"])
        return result

    def query_position_uuid(self, uuid: str):
        result = self.cursor.execute(
            "SELECT * FROM positions WHERE uuid=?", (uuid,)
        ).fetchone()
        if result is not None:
            result = dict(result)
            result["block"] = True if result["block"] else False
        return result

    def query_positions(
        self,
        *,
        uri: Optional[Union[str, tuple]] = NotSet(),
        block: Optional[bool] = NotSet(),
        etype: Optional[Union[str, tuple]] = NotSet(),
        parent_uuid: Optional[Union[str, tuple]] = NotSet(),
        uuid: Optional[Union[str, tuple]] = NotSet(),
        **kwargs,
    ) -> Iterable[dict]:
        conditions = []
        replacements = []
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
                conditions.append(f"{key} IN ({','.join('?' for _ in value)})")
                replacements.extend([bool_to_int(v) for v in value])
            else:
                conditions.append(f"{key}=?")
                replacements.append(bool_to_int(value))

        if conditions:
            results = self.cursor.execute(
                f"SELECT * FROM positions WHERE {' AND '.join(conditions)}",
                replacements,
            ).fetchall()
        else:
            results = self.cursor.execute("SELECT * FROM positions").fetchall()
        for result in results:
            result = dict(result)
            result["block"] = True if result["block"] else False
            yield result

    def query_at_position(self, uri: str, line: int, character: int) -> dict:
        results = self.cursor.execute(
            "SELECT * FROM positions WHERE uri=? AND startLine<=? AND endLine>=?",
            (uri, line, line),
        ).fetchall()
        # find the result that has the smallest line range
        # TODO also smallest character range?
        # TODO can this be achieved in query syntax
        final_result = None
        final_line_range = None
        for result in results:
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
        if final_result is None:
            return None
        final_result = dict(final_result)
        final_result["block"] = True if final_result["block"] else False
        return final_result
