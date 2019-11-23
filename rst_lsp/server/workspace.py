import io
import os
import pathlib
import re
from typing import Dict, List

from rst_lsp.database.tinydb import Database
from rst_lsp.analyse.main import init_sphinx
from . import uri_utils as uris
from .utils import find_parents
from .datatypes import Position, TextDocument, TextEdit


# TODO: this is not the best e.g. we capture numbers
RE_START_WORD = re.compile("[A-Za-z_0-9]*$")
RE_END_WORD = re.compile("^[A-Za-z_0-9]*")


class Config:
    """Store configuration settings."""

    def __init__(self, root_uri, init_opts, process_id, capabilities):
        self._root_path = uris.to_fs_path(root_uri)
        self._root_uri = root_uri
        self._init_opts = init_opts
        self._process_id = process_id
        self._capabilities = capabilities
        self._settings = {}

    @property
    def init_opts(self):
        return self._init_opts

    @property
    def root_uri(self):
        return self._root_uri

    @property
    def process_id(self):
        return self._process_id

    @property
    def capabilities(self):
        return self._capabilities

    @property
    def settings(self):
        return self._settings

    def update(self, settings: dict):
        """Recursively merge the given settings into the current settings."""
        self._settings = settings


class Workspace(object):
    """Store an in-memory representation of the open workspace files."""

    def __init__(self, root_uri: str, server, config: Config):
        self._config = config
        self._root_uri = root_uri
        self._server = server
        self._root_uri_scheme = uris.urlparse(self._root_uri)[0]
        self._root_path = uris.to_fs_path(self._root_uri)
        self._docs = {}
        self._init_database()

    def _init_database(self):
        db_path = os.path.join(self.root_path, ".rst-lsp-db.json")
        self._db = Database(db_path)
        with init_sphinx(confdir=None) as sphinx_init:
            self._db.update_conf_file(None, sphinx_init.roles, sphinx_init.directives)
        self.server.log_message(f"Created database at: {db_path}")

    @property
    def documents(self):
        return self._docs

    @property
    def database(self) -> Database:
        return self._db

    @property
    def root_path(self) -> str:
        return self._root_path

    @property
    def root_uri(self) -> str:
        return self._root_uri

    @property
    def server(self):
        return self._server

    def is_local(self):
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    def get_document(self, doc_uri: str):
        """Return a managed document if-present, else create one pointing at disk.

        See https://github.com/Microsoft/language-server-protocol/issues/177
        """
        return self._docs.get(doc_uri) or self._create_document(doc_uri)

    def put_document(self, document: TextDocument):
        self._docs[document["uri"]] = self._create_document(document)

    def rm_document(self, doc_uri):
        self._docs.pop(doc_uri)

    def update_document(self, doc_uri, change: TextEdit, version=None):
        self._docs[doc_uri].apply_change(change)
        self._docs[doc_uri].version = version

    def update_config(self, config):
        self._config = config
        for doc_uri in self.documents:
            self.get_document(doc_uri).update_config(config)

    def source_roots(self, document_path: str, filename: str = "conf.py"):
        """Return the source roots for the given document."""
        files = find_parents(self._root_path, document_path, [filename]) or []
        return list(set((os.path.dirname(project_file) for project_file in files))) or [
            self._root_path
        ]

    def _create_document(self, document: TextDocument):
        return Document(
            document["uri"],
            source=document["text"],
            version=document["version"],
            config=self._config,
            workspace=self,
        )


class Document:
    """Store an in-memory representation of a source file."""

    def __init__(
        self, uri, source=None, version=None, local=True, config=None, workspace=None,
    ):
        self.uri = uri
        self.version = version
        self.path = uris.to_fs_path(uri)
        self.filename = os.path.basename(self.path)

        self._config = config
        self._workspace = workspace
        self._local = local
        self._source = source

    @property
    def workspace(self) -> Workspace:
        return self._workspace

    def __str__(self):
        return str(self.uri)

    @property
    def lines(self) -> List[str]:
        return self.source.splitlines(True)

    @property
    def source(self) -> str:
        if self._source is None:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()
        return self._source

    def update_config(self, config: Config):
        self._config = config

    def apply_change(self, change: TextEdit):
        """Apply a change to the document."""
        text = change["text"]
        change_range = change["range"]

        if not change_range:
            # The whole file has changed
            self._source = text
            return

        start_line = change_range["start"]["line"]
        start_col = change_range["start"]["character"]
        end_line = change_range["end"]["line"]
        end_col = change_range["end"]["character"]

        # Check for an edit occuring at the very end of the file
        if start_line == len(self.lines):
            self._source = self.source + text
            return

        new = io.StringIO()

        # Iterate over the existing document until we hit the edit range,
        # at which point we write the new text, then loop until we hit
        # the end of the range and continue writing.
        for i, line in enumerate(self.lines):
            if i < start_line:
                new.write(line)
                continue

            if i > end_line:
                new.write(line)
                continue

            if i == start_line:
                new.write(line[:start_col])
                new.write(text)

            if i == end_line:
                new.write(line[end_col:])

        self._source = new.getvalue()

    def get_line(self, position: Position) -> str:
        """Return the position's line."""
        return self.lines[position["line"]]

    def get_line_before(self, position: Position) -> str:
        """Return the section of the position's line before the position."""
        return self.lines[position["line"]][:position["character"]]

    def offset_at_position(self, position: Position):
        """Return the byte-offset pointed at by the given position."""
        return position["character"] + len("".join(self.lines[: position["line"]]))

    def word_at_position(self, position: Position, start_regex=None, end_regex=None):
        """Get the word under the cursor returning the start and end positions."""
        if position["line"] >= len(self.lines):
            return ""

        line = self.lines[position["line"]]
        i = position["character"]
        # Split word in two
        start = line[:i]
        end = line[i:]

        # Take end of start and start of end to find word
        # These are guaranteed to match, even if they match the empty string
        start_regex = start_regex or RE_START_WORD
        end_regex = end_regex or RE_END_WORD
        m_start = start_regex.findall(start)
        m_end = end_regex.findall(end)

        return m_start[0] + m_end[-1]


def match_uri_to_workspace(
    uri: str, workspaces: Dict[str, Workspace], default: Workspace
) -> Workspace:
    """Find the workspace containing the URI."""
    if uri is None:
        return None
    max_len, chosen_workspace = -1, None
    path = pathlib.Path(uri).parts
    for workspace in workspaces:
        workspace_parts = pathlib.Path(workspace).parts
        if len(workspace_parts) > len(path):
            continue
        match_len = 0
        for workspace_part, path_part in zip(workspace_parts, path):
            if workspace_part == path_part:
                match_len += 1
        if match_len > 0:
            if match_len > max_len:
                max_len = match_len
                chosen_workspace = workspace
    return workspaces.get(chosen_workspace, default)
