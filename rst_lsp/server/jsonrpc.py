"""Server implementation of the JSON RPC 2.0 protocol.

Originally adapted from:
https://github.com/palantir/python-language-server/blob/b08891f9345a5bbd543c657d1251cceed9f79b01/pyls/python_ls.py

"""
# TODO how to show status bar of server status (https://github.com/onivim/oni/pull/524)
from functools import partial
import logging
import os
import socketserver
import threading
from typing import Any, Dict, Optional, Union

import attr

from pyls_jsonrpc.dispatchers import MethodDispatcher
from pyls_jsonrpc.endpoint import Endpoint
from pyls_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

from . import constants, utils
from . import uri_utils as uris

log = logging.getLogger(__name__)

PARENT_PROCESS_WATCH_INTERVAL = 10  # 10 s
MAX_WORKERS = 64
# SOURCE_FILE_EXTENSIONS = (".rst",)
# CONFIG_FILES = ("conf.py",)


@attr.s(kw_only=True)
class TextDocument:
    uri: str = attr.ib(None)
    languageId: str = attr.ib(None)
    version: int = attr.ib(None)
    text: str = attr.ib(None)


# {"line": "integer", "character": "integer"}, zero-based
# PositionType = Dict[str, int]
# {"start": "Position", "end": "Position"}
# RangeType = Dict[str, PositionType]

# available server to client messages (self._endpoint.notify(name, params={...})):
    # 'textDocument/publishDiagnostics'
    # 'window/showMessage'
    # 'window/logMessage'
    # 'workspace/applyEdit' (use self._endpoint.request instead)


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
        log.debug("Shutting down server")
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
        log.info("Serving %s on (%s, %s)", handler_class.__name__, bind_addr, port)
        server.serve_forever()
    finally:
        log.info("Shutting down")
        server.server_close()


def start_io_lang_server(rfile, wfile, check_parent_process, handler_class):
    if not issubclass(handler_class, RstLanguageServer):
        raise ValueError("Handler class must be an instance of RstLanguageServer")
    log.info("Starting %s IO language server", handler_class.__name__)
    server = handler_class(rfile, wfile, check_parent_process)
    server.start()


class RstLanguageServer(MethodDispatcher):
    """ Implementation of the Microsoft VSCode Language Server Protocol
    https://github.com/Microsoft/language-server-protocol/blob/master/versions/protocol-1-x.md
    """

    def __init__(self, rx, tx, check_parent_process=False):

        self.root_uri = None
        self.watching_thread = None
        self.uri_workspace_mapper = {}

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

    def __getitem__(self, item):
        """Override getitem to fallback through multiple dispatchers."""
        if self._shutdown and item != "exit":
            # exit is the only allowed method during shutdown
            log.debug("Ignoring non-exit method during shutdown: %s", item)
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
        self._endpoint.shutdown()
        self._jsonrpc_stream_reader.close()
        self._jsonrpc_stream_writer.close()

    def capabilities(self):
        server_capabilities = {
            # Defines how text documents are synced
            "textDocumentSync": {
                # TODO ideally document sync would be incremental
                "change": constants.TextDocumentSyncKind.FULL,
                "save": {"includeText": True},
                "openClose": True,
                # "willSave": False,
                # "willSaveWaitUntil": False
            },
            # "workspace": {
            #     "workspaceFolders": {"supported": True, "changeNotifications": True}
            # },
            # features provided
            # "codeActionProvider": True,
            # "codeLensProvider": {
            #     "resolveProvider": False,
            # },
            # "completionProvider": {
            #     "resolveProvider": False,
            #     "triggerCharacters": [":"],
            # },
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
        log.info("Server capabilities: %s", server_capabilities)
        return server_capabilities

    def m_initialize(
        self,
        processId: Optional[int] = None,
        rootUri: Optional[int] = None,
        rootPath: Optional[str] = None,
        initializationOptions: Optional[Any] = None,
        **_kwargs
    ):
        log.debug(
            "Language server initialized with %s %s %s %s",
            processId,
            rootUri,
            rootPath,
            initializationOptions,
        )
        if rootUri is None:
            rootUri = uris.from_fs_path(rootPath) if rootPath is not None else ""
        self.root_uri = rootUri

        if (
            self._check_parent_process
            and processId is not None
            and self.watching_thread is None
        ):

            def watch_parent_process(pid):
                # exit when the given pid is not alive
                if not utils.is_process_alive(pid):
                    log.info("parent process %s is not alive, exiting!", pid)
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

    def m_text_document__did_open(self, textDocument: dict = None, **_kwargs):
        pass

    def m_text_document__did_close(self, textDocument: dict = None, **_kwargs):
        pass

    def m_text_document__did_save(self, textDocument: dict = None, **_kwargs):
        pass

    def m_text_document__did_change(
        self, contentChanges: list = None, textDocument: dict = None, **_kwargs
    ):
        pass

    def m_text_document__did_save(self, textDocument: dict = None, **_kwargs):
        pass

    def m_text_document__folding_range(self, textDocument: dict = None, **_kwargs):
        return []

