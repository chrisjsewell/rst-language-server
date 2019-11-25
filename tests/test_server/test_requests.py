import os
from textwrap import dedent

import pytest
from pyls_jsonrpc.exceptions import JsonRpcMethodNotFound

CALL_TIMEOUT = 10


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
                "text": dedent(
                    """\
                    title
                    -----

                    abc

                    title2
                    ======

                    def
                    """
                ),
            }
        },
    )
    response3 = client_server._endpoint.request(
        "text_document/folding_range",
        {"textDocument": {"uri": "uri123", "languageId": "str", "version": 1}},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)


def test_document_symbols(client_server, data_regression):
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
                "text": dedent(
                    """\
                    title
                    -----

                    abc

                    title2
                    ======

                    def
                    """
                ),
            }
        },
    )
    response3 = client_server._endpoint.request(
        "text_document/document_symbol",
        {"textDocument": {"uri": "uri123", "languageId": "str", "version": 1}},
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)


def test_completion(client_server, data_regression):
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
                "text": dedent(
                    """\
                    :
                    """
                ),
            }
        },
    )
    response3 = client_server._endpoint.request(
        "text_document/completion",
        {
            "textDocument": {"uri": "uri123", "languageId": "str", "version": 1},
            "position": {"line": 0, "character": 1},
        },
    ).result(timeout=CALL_TIMEOUT)
    data_regression.check(response3)
