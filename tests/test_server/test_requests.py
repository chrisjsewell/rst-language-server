import os
from textwrap import dedent

import pytest
from pyls_jsonrpc.exceptions import JsonRpcMethodNotFound

CALL_TIMEOUT = 10


def open_test_doc(client_server, content, uri="uri123", initialize=True):
    if initialize:
        response = client_server._endpoint.request(
            "initialize",
            {"rootPath": os.path.dirname(__file__), "initializationOptions": {}},
        ).result(timeout=CALL_TIMEOUT)
        assert "capabilities" in response
    client_server._endpoint.request(
        "text_document/did_open",
        {
            "textDocument": {
                "uri": "uri123",
                "languageId": "str",
                "version": 1,
                "text": content,
            }
        },
    )
    return {"uri": uri, "languageId": "str", "version": 1}


def test_missing_message(client_server):  # pylint: disable=redefined-outer-name
    with pytest.raises(JsonRpcMethodNotFound):
        client_server._endpoint.request("unknown_method").result(timeout=CALL_TIMEOUT)


def test_initialize(client_server, data_regression):
    future = client_server._endpoint.request(
        "initialize",
        {"rootPath": os.path.dirname(__file__), "initializationOptions": {}},
    )
    response = future.result(timeout=CALL_TIMEOUT)
    data_regression.check(response)


# TODO how to test notifications, like publish diagnostics?


def test_folding_provider(client_server, data_regression):
    content = dedent(
        """\
        title
        -----

        abc

        title2
        ======

        def
        """
    )
    doc = open_test_doc(client_server, content)
    response3 = client_server._endpoint.request(
        "text_document/folding_range", {"textDocument": doc},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)


def test_document_symbols(client_server, data_regression):
    content = dedent(
        """\
        title
        -----

        |abc|

        :ref`abc`

        title2
        ======

        .. code:: python

            print("hi")

        def
        """
    )
    doc = open_test_doc(client_server, content)
    response3 = client_server._endpoint.request(
        "text_document/document_symbol", {"textDocument": doc},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)


def test_completion(client_server, data_regression):
    doc = open_test_doc(client_server, ":\n")
    response3 = client_server._endpoint.request(
        "text_document/completion",
        {"textDocument": doc, "position": {"line": 0, "character": 1}},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)


def test_hover(client_server, data_regression):
    doc = open_test_doc(client_server, ":index:`abc`\n")
    response3 = client_server._endpoint.request(
        "text_document/hover",
        {"textDocument": doc, "position": {"line": 0, "character": 1}},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)
