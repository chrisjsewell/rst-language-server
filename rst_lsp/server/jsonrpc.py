"""Server implementation of the JSON RPC 2.0 protocol.

Originally adapted from:
https://github.com/palantir/python-language-server/blob/b08891f9345a5bbd543c657d1251cceed9f79b01/pyls/python_ls.py

"""
# TODO how to show status bar of server status (https://github.com/onivim/oni/pull/524)
from functools import partial, wraps
from concurrent.futures import Future
import inspect
import logging
import os
import socketserver
import threading
from typing import Any, Dict, List, Optional

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import constants, utils
from . import uri_utils as uris
from .workspace import Config, Document, Workspace
from .workspace import match_uri_to_workspace as uri2workspace
from .datatypes import CompletionList, Position, TextDocument, TextEdit
from .plugins import PluginTypes

logger = logging.getLogger(__name__)

PARSING_DEBOUNCE = 0.5  # 500 ms
PARENT_PROCESS_WATCH_INTERVAL = 10  # 10 s
MAX_WORKERS = 64
# SOURCE_FILE_EXTENSIONS = (".rst",)
# CONFIG_FILES = ("conf.py",)

CONFIG_NAMESPACE = "rst_lsp"


class _StreamHandlerWrapper(socketserver.StreamRequestHandler, object):
    """A wrapper class that is used to construct a custom handler class."""

    delegate = None

    def setup(self):
        super(_StreamHandlerWrapper, self).setup()
        self.delegate = self.DELEGATE_CLASS(self.rfile, self.wfile)

    def handle(self):
        try:
            self.delegate.start()
        except OSError as e:
            if os.name == "nt":
                # Catch and pass on ConnectionResetError when parent process dies
                if isinstance(e, WindowsError) and e.winerror == 10054:
                    pass

        self.SHUTDOWN_CALL()


def start_tcp_lang_server(bind_addr, port, check_parent_process, handler_class):
    if not issubclass(handler_class, RstLanguageServer):
        raise ValueError("Handler class must be an instance of PythonLanguageServer")

    def shutdown_server(*args):
        # pylint: disable=unused-argument
        logger.debug("Shutting down server")
        # Shutdown call must be done on a thread, to prevent deadlocks
        stop_thread = threading.Thread(target=server.shutdown)
        stop_thread.start()

    # Construct a custom wrapper class around the user's handler_class
    wrapper_class = type(
        handler_class.__name__ + "Handler",
        (_StreamHandlerWrapper,),
        {
            "DELEGATE_CLASS": partial(
                handler_class, check_parent_process=check_parent_process
            ),
            "SHUTDOWN_CALL": shutdown_server,
        },
    )

    server = socketserver.TCPServer((bind_addr, port), wrapper_class)
    server.allow_reuse_address = True

    try:
        logger.info("Serving %s on (%s, %s)", handler_class.__name__, bind_addr, port)
        server.serve_forever()
    finally:
        logger.info("Shutting down")
        server.server_close()


def start_io_lang_server(rfile, wfile, check_parent_process, handler_class):
    if not issubclass(handler_class, RstLanguageServer):
        raise ValueError("Handler class must be an instance of RstLanguageServer")
    logger.info("Starting %s IO language server", handler_class.__name__)
    server = handler_class(rfile, wfile, check_parent_process)
    server.start()


def debounce(interval_s, keyed_by=None):
    """Debounce calls to this function until interval_s seconds have passed."""

    def wrapper(func):
        timers = {}
        lock = threading.Lock()

        @wraps(func)
        def debounced(*args, **kwargs):
            call_args = inspect.getcallargs(func, *args, **kwargs)
            key = call_args[keyed_by] if keyed_by else None

            def run():
                with lock:
                    del timers[key]
                return func(*args, **kwargs)

            with lock:
                old_timer = timers.get(key)
                if old_timer:
                    old_timer.cancel()

                timer = threading.Timer(interval_s, run)
                timers[key] = timer
                timer.start()

        return debounced

    return wrapper


class RstLanguageServer(MethodDispatcher):
    """ Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md
    """

    def capabilities(self) -> dict:
        server_capabilities = {
            # Defines how text documents are synced
            "textDocumentSync": {
                "change": constants.TextDocumentSyncKind.INCREMENTAL,
                "save": {"includeText": True},
                "openClose": True,
            },
            "workspace": {
                "workspaceFolders": {"supported": True, "changeNotifications": True}
            },
            # features provided
            # "codeActionProvider": True,
            # "codeLensProvider": {
            #     "resolveProvider": False,
            # },
            "completionProvider": {
                "resolveProvider": False,
                "triggerCharacters": [],  # [":"],
            },
            # "documentFormattingProvider": True,
            # "documentHighlightProvider": True,
            # "documentRangeFormattingProvider": True,
            # "documentSymbolProvider": True,
            # "definitionProvider": True,
            # "executeCommandProvider": {
            #     "commands": flatten(self._hook("pyls_commands"))
            # },
            # "hoverProvider": True,
            # "referencesProvider": True,
            # "renameProvider": True,
            "foldingRangeProvider": True,
            # "signatureHelpProvider": {"triggerCharacters": []},
            # "experimental": any,
        }
        logger.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def __init__(self, rx, tx, check_parent_process=False):
        """Initialise the server."""
        self.root_uri = None
        self.config = None  # type: Optional[Config]
        self.workspaces = {}  # type: Dict[str, Workspace]
        self.watching_thread = None

        self._jsonrpc_stream_reader = JsonRpcStreamReader(rx)
        self._jsonrpc_stream_writer = JsonRpcStreamWriter(tx)
        self._check_parent_process = check_parent_process
        self._endpoint = Endpoint(
            self, self._jsonrpc_stream_writer.write, max_workers=MAX_WORKERS
        )
        self._dispatchers = []
        self._shutdown = False

    def start(self):
        """Entry point for the server."""
        self._jsonrpc_stream_reader.listen(self._endpoint.consume)

    def show_message(self, message: str, msg_type: int = constants.MessageType.Info):
        """Request the client show a pop-up message."""
        self._endpoint.notify(
            "window/showMessage", params={"type": msg_type, "message": message}
        )

    def log_message(self, message: str, msg_type: int = constants.MessageType.Info):
        """Request the client log a message (in the servers output space)."""
        self._endpoint.notify(
            "window/logMessage", params={"type": msg_type, "message": str(message)}
        )

    def show_message_request(
        self,
        message: str,
        actions: List[dict] = (),
        msg_type: int = constants.MessageType.Info,
    ) -> Future:
        """Request the client show a pop-up message, with action buttons.

        Parameters
        ----------
        actions: list[dict]
            e.g. [{"title": "A"}, {"title": "B"}]
        """
        # for use see: https://github.com/Microsoft/language-server-protocol/issues/230
        return self._endpoint.request(
            "window/showMessageRequest",
            params={"type": msg_type, "message": message, "actions": list(actions)},
        )

    def request_config(self, items: List[dict]) -> Future:
        """Request configuration settings from the client.

        Parameters
        ----------
        items : list[dict]
            e.g. [{"section": "rst_lsp"}]
        """
        return self._endpoint.request(
            "workspace/configuration", params={"items": items},
        )

    def notify_lint(self, doc_uri: str, diagnostics: List[dict]):
        """Request configuration settings from the client."""
        self._endpoint.notify(
            "textDocument/publishDiagnostics",
            params={"uri": doc_uri, "diagnostics": diagnostics},
        )


    # also available
    # 'workspace/applyEdit' request

    def __getitem__(self, item):
        """Override getitem to fallback through multiple dispatchers."""
        if self._shutdown and item != "exit":
            # exit is the only allowed method during shutdown
            logger.debug("Ignoring non-exit method during shutdown: %s", item)
            raise KeyError
        try:
            return super(RstLanguageServer, self).__getitem__(item)
        except KeyError:
            # Fallback through extra dispatchers
            for dispatcher in self._dispatchers:
                try:
                    return dispatcher[item]
                except KeyError:
                    continue

        raise KeyError()

    def m_shutdown(self, **_kwargs):
        self._shutdown = True
        return None

    def m_exit(self, **_kwargs):
        # Note: LSP protocol indicates that the server process should remain alive after
        # the client's Shutdown request, and wait for the client's Exit notification.
        for workspace in self.workspaces.values():
            workspace.close()
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def match_uri_to_workspace(self, uri: str) -> Workspace:
        return uri2workspace(uri, self.workspaces, self.workspace)

    def match_uri_to_document(self, uri: str) -> Document:
        workspace = uri2workspace(uri, self.workspaces, self.workspace)
        return workspace.get_document(uri)

    def call_plugins(self, hook_name, doc_uri: Optional[str] = None, **kwargs):
        """Calls hook_name and returns a list of results from all registered handlers"""
        logger.debug("calling plugins")
        workspace = self.match_uri_to_workspace(doc_uri)
        doc = workspace.get_document(doc_uri) if doc_uri else None
        hook_handlers = self.config.plugin_manager.subset_hook_caller(
            hook_name, self.config.disabled_plugins
        )
        return hook_handlers(
            config=self.config, workspace=workspace, document=doc, **kwargs
        )

    @debounce(PARSING_DEBOUNCE, keyed_by="doc_uri")
    def lint(self, doc_uri, is_saved):
        workspace = self.match_uri_to_workspace(doc_uri)
        if doc_uri in workspace.documents:
            # workspace.publish_diagnostics(
            diagnostics = [
                {
                    "source": "flake8",
                    "code": "asdgasdg",
                    "range": {
                        "start": {"line": 1, "character": 7},
                        "end": {"line": 1, "character": 9},
                    },
                    "message": "hallo",
                    "severity": constants.DiagnosticSeverity.Warning,
                }
            ]
            # flatten(self.call_plugins('rst_lint', doc_uri, is_saved=is_saved))
            self.notify_lint(doc_uri, diagnostics)

    def m_initialize(
        self,
        processId: Optional[int] = None,
        rootUri: Optional[int] = None,
        rootPath: Optional[str] = None,
        initializationOptions: Optional[Any] = None,
        **_kwargs,
    ):
        logger.debug(
            "Language server initialized with %s %s %s %s",
            processId,
            rootUri,
            rootPath,
            initializationOptions,
        )
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ""
        self.workspaces.pop(self.root_uri, None)
        self.root_uri = rootUri
        self.config = Config(
            rootUri,
            initializationOptions or {},
            processId,
            _kwargs.get("capabilities", {}),
        )
        self.workspace = Workspace(rootUri, server=self, config=self.config)
        self.workspaces[rootUri] = self.workspace

        if (
            self._check_parent_process
            and processId is not None
            and self.watching_thread is None
        ):

            def watch_parent_process(pid):
                # exit when the given pid is not alive
                if not utils.is_process_alive(pid):
                    logger.info("parent process %s is not alive, exiting!", pid)
                    self.m_exit()
                else:
                    threading.Timer(
                        PARENT_PROCESS_WATCH_INTERVAL, watch_parent_process, args=[pid]
                    ).start()

            self.watching_thread = threading.Thread(
                target=watch_parent_process, args=(processId,)
            )
            self.watching_thread.daemon = True
            self.watching_thread.start()

        return {"capabilities": self.capabilities()}

    def m_initialized(self, **_kwargs):
        pass

    def m_workspace__did_change_configuration(self, settings=None):
        self.config.update((settings or {}).get(CONFIG_NAMESPACE, {}))
        for workspace_uri in self.workspaces:
            workspace = self.workspaces[workspace_uri]
            workspace.update_config(self.config)

    def m_workspace__did_change_workspace_folders(
        self, added=None, removed=None, **_kwargs
    ):
        for removed_info in removed:
            removed_uri = removed_info["uri"]
            self.workspaces.pop(removed_uri)

        for added_info in added:
            added_uri = added_info["uri"]
            self.workspaces[added_uri] = Workspace(
                added_uri, server=self, config=self.config
            )

        # Migrate documents that are on the root workspace and have a better match now
        doc_uris = list(self.workspace.documents.keys())
        for uri in doc_uris:
            doc = self.workspace._docs.pop(uri)
            new_workspace = self.match_uri_to_workspace(uri)
            new_workspace._docs[uri] = doc

    def m_workspace__did_change_watched_files(self, changes=None, **_kwargs):
        pass  # TODO

    def m_text_document__did_open(self, textDocument: TextDocument, **_kwargs):
        workspace = self.match_uri_to_workspace(textDocument["uri"])
        workspace.put_document(textDocument)
        self.lint(textDocument["uri"], is_saved=False)

    def m_text_document__did_close(self, textDocument: TextDocument, **_kwargs):
        workspace = self.match_uri_to_workspace(textDocument["uri"])
        workspace.rm_document(textDocument["uri"])

    def m_text_document__did_save(self, textDocument: TextDocument, **_kwargs):
        pass  # Already taken care of by change

    def m_text_document__did_change(
        self, contentChanges: List[TextEdit], textDocument: TextDocument, **_kwargs
    ):
        workspace = self.match_uri_to_workspace(textDocument["uri"])
        for change in contentChanges:
            workspace.update_document(
                textDocument["uri"], change, version=textDocument.get("version")
            )

    # FEATURES
    # --------

    def m_text_document__folding_range(self, textDocument: TextDocument, **_kwargs):
        return self.call_plugins(
            PluginTypes.rst_folding_range.value, textDocument["uri"]
        )

    def m_text_document__completion(
        self, textDocument: TextDocument, position: Position, **_kwargs
    ) -> CompletionList:
        completions = self.call_plugins(
            PluginTypes.rst_completions.value, textDocument["uri"], position=position
        )
        return {"isIncomplete": False, "items": utils.flatten(completions)}
