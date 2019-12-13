# from concurrent.futures import Future
import io
import logging
import os
import pathlib
import re
from typing import Dict, List

from rst_lsp.database.tinydb import SynchronizedDatabase
from rst_lsp.sphinx_ext.main import (
    assess_source,
    create_sphinx_app,
    # find_all_files,
    retrieve_namespace,
    SourceAssessResult,
    SphinxAppEnv,
)
from . import uri_utils as uris
from .constants import MessageType
from .utils import find_parents
from .datatypes import Position, TextDocument, TextEdit
from .plugin_manager import create_manager

logger = logging.getLogger(__name__)

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
        self._plugin_manager = create_manager(logger)
        # TODO extract settings from plugin manager
        self._update_disabled_plugins()

    def _update_disabled_plugins(self):
        # All plugins default to enabled
        self._disabled_plugins = [
            plugin
            for name, plugin in self.plugin_manager.list_name_plugin()
            if not self.settings.get("plugins", {}).get(name, {}).get("enabled", True)
        ]
        logger.info("Disabled plugins: %s", self._disabled_plugins)

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

    @property
    def plugin_manager(self):
        return self._plugin_manager

    @property
    def disabled_plugins(self):
        return self._disabled_plugins

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
        self._open_docs = {}
        # TODO how to utilise persistent DB?
        self._db = SynchronizedDatabase()
        self._update_env()

    def _update_env(self):
        """Update the sphinx application."""
        # TODO how to watch conf.py for changes? (or at least have command to update)
        # TODO use self.source_roots to find conf path?
        # TODO allow source directory to be different to conf path
        conf_path = self._config.settings.get("conf_path", None)
        logger.debug(f"Settings: {self._config.settings}")
        if conf_path and not os.path.exists(conf_path):
            self.server.show_message(
                f"The path set in `rst_lsp.conf_path` does not exist: {conf_path}",
                msg_type=MessageType.Error,
            )
            conf_path = None
        elif conf_path:
            conf_path = os.path.realpath(conf_path)
        logger.debug(f"Using conf dir: {conf_path}")
        try:
            self._app_env = create_sphinx_app(
                os.path.dirname(conf_path) if conf_path else None
            )
        except Exception as err:
            self.server.show_message(
                (
                    "An error occurred creating a sphinx application from "
                    f"`rst_lsp.conf_path`: {conf_path}.\n\n"
                    f"{err}"
                ),
                msg_type=MessageType.Error,
            )
            conf_path = None
            self._app_env = create_sphinx_app(None)
        roles, directives = retrieve_namespace(self._app_env)
        self._db.update_conf_file(conf_path, roles, directives)

    def close(self):
        self._db.close()

    @property
    def documents(self) -> dict:
        return self._open_docs

    @property
    def database(self) -> SynchronizedDatabase:
        """Return the workspace database.

        If any document's source text hasn't been parsed/assessed, since its last change
        (or config update), then that will be done, and the database updated,
        before returning.
        """
        for doc in self._open_docs.values():
            result = doc.get_assessment()  # type: SourceAssessResult
            self._db.update_doc(
                doc.uri,
                positions=result.positions,
                references=result.references,
                doc_symbols=result.doc_symbols,
                lints=result.linting,
            )
        return self._db

    @property
    def app_env(self) -> SphinxAppEnv:
        return self._app_env

    @property
    def root_path(self) -> str:
        return self._root_path

    @property
    def root_uri(self) -> str:
        return self._root_uri

    @property
    def server(self):
        return self._server

    @property
    def config(self):
        return self._config

    def get_document(self, doc_uri: str):
        """Return a managed document if-present, else create one pointing at disk.

        See https://github.com/Microsoft/language-server-protocol/issues/177
        """
        doc = self._open_docs.get(doc_uri, None)
        if doc is None:
            doc = self._create_document({"uri": doc_uri})
        return doc

    def put_document(self, document: TextDocument):
        self._open_docs[document["uri"]] = self._create_document(document)

    def rm_document(self, doc_uri):
        self._open_docs.pop(doc_uri)

    def update_document(self, doc_uri, change: TextEdit, version=None):
        self._open_docs[doc_uri].apply_change(change)
        self._open_docs[doc_uri].version = version

    def update_config(self, config):
        self._config = config
        self._update_env()
        for doc_uri in self.documents:
            self.get_document(doc_uri).update_config(config)

    # TODO parse all files in background
    #     conf_path = (self._db.query_conf_file() or {}).get("uri", None)
    #     if not conf_path:
    #         return
    #     exclude_patterns = (
    #         self.app_env.app.config.exclude_patterns
    #         + self.app_env.app.config.templates_path
    #     )
    #     future = self._server._endpoint._executor_service.submit(
    #         find_all_files,
    #         srcdir=os.path.dirname(conf_path),
    #         exclude_patterns=exclude_patterns,
    #     )
    #     future.add_done_callback(self.notify_files)

    # def notify_files(self, future: Future):
    #     if future.cancelled():
    #         return
    #     self._rst_files = future.result()

    @property
    def is_local(self):
        """Test if the file is local (i.e. can be accessed by ``os``)."""
        return (
            self._root_uri_scheme == "" or self._root_uri_scheme == "file"
        ) and os.path.exists(self._root_path)

    def source_roots(self, document_path: str, filename: str = "conf.py"):
        """Return the source roots for the given document."""
        if not self.is_local:
            return None
        files = find_parents(self._root_path, document_path, [filename]) or []
        return list(set((os.path.dirname(project_file) for project_file in files))) or [
            self._root_path
        ]

    def _create_document(self, document: TextDocument):
        return Document(
            document["uri"],
            source=document.get("text", None),
            version=document.get("version", None),
            config=self._config,
            workspace=self,
        )


class Document:
    """Store an in-memory representation of a source file.

    The documents source text is kept in-sync with the clients,
    by applying ``TextEdit`` changes, on notification by the client.

    docutils/sphinx parsing of the source text is done lazily,
    whenever ``doc.get_assessment()`` is called,
    and the source text/configuration has changed.
    """

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
        self._assessment = None

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

    def get_assessment(self) -> SourceAssessResult:
        if self._assessment is None:
            # TODO partial reassessment of source, given applied changes
            self._assessment = assess_source(
                self.source, self.workspace.app_env, doc_uri=self.uri
            )
        return self._assessment

    def update_config(self, config: Config):
        self._config = config
        self._assessment = None

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
        self._assessment = None

    def get_line(self, position: Position) -> str:
        """Return the position's line."""
        return self.lines[position["line"]]

    def get_line_before(self, position: Position) -> str:
        """Return the section of the position's line before the position."""
        return self.lines[position["line"]][: position["character"]]

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
