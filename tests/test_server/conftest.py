import os
import multiprocessing
from threading import Thread

import pytest

from rst_lsp.server.jsonrpc import start_io_lang_server, RstLanguageServer

CALL_TIMEOUT = 10


def start_client(client):
    client.start()


class ClientServer(object):
    """ A class to setup a client/server pair """

    def __init__(self, check_parent_process=False):
        # Client to Server pipe
        csr, csw = os.pipe()
        # Server to client pipe
        scr, scw = os.pipe()

        ParallelKind = multiprocessing.Process if os.name != "nt" else Thread

        self.process = ParallelKind(
            target=start_io_lang_server,
            args=(
                os.fdopen(csr, "rb"),
                os.fdopen(scw, "wb"),
                check_parent_process,
                RstLanguageServer,
            ),
        )
        self.process.start()

        self.client = RstLanguageServer(
            os.fdopen(scr, "rb"), os.fdopen(csw, "wb"), start_io_lang_server
        )
        self.client_thread = Thread(target=start_client, args=[self.client])
        self.client_thread.daemon = True
        self.client_thread.start()


@pytest.fixture
def client_server():
    """ A fixture that sets up a client/server pair and shuts down the server
    This client/server pair does not support checking parent process aliveness
    """
    client_server_pair = ClientServer()

    yield client_server_pair.client

    shutdown_response = client_server_pair.client._endpoint.request("shutdown").result(
        timeout=CALL_TIMEOUT
    )
    assert shutdown_response is None
    client_server_pair.client._endpoint.notify("exit")


@pytest.fixture
def client_exited_server():
    """A fixture that sets up a client/server pair.

    This supports checking parent process aliveness,
    and asserting the server has already exited
    """
    client_server_pair = ClientServer(True)

    yield client_server_pair

    assert client_server_pair.process.is_alive() is False
