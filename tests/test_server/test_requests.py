import os

import pytest
from pyls_jsonrpc.exceptions import JsonRpcMethodNotFound

CALL_TIMEOUT = 10


def test_missing_message(client_server):  # pylint: disable=redefined-outer-name
    with pytest.raises(JsonRpcMethodNotFound):
        client_server._endpoint.request('unknown_method').result(timeout=CALL_TIMEOUT)


def test_initialize(client_server):
    response = client_server._endpoint.request(
        "initialize",
        {"rootPath": os.path.dirname(__file__), "initializationOptions": {}},
    ).result(timeout=CALL_TIMEOUT)
    assert "capabilities" in response
    assert "textDocumentSync" in response["capabilities"]


def test_folding_provider(client_server):
    response = client_server._endpoint.request(
        "initialize",
        {"rootPath": os.path.dirname(__file__), "initializationOptions": {}},
    ).result(timeout=CALL_TIMEOUT)
    assert "capabilities" in response
    response2 = client_server._endpoint.request(
        "text_document/folding_range",
        {
            "textDocument": {
                "uri": "string",
                "languageId": "str",
                "version": 1,
                "text": "string",
            }
        },
    ).result(timeout=CALL_TIMEOUT)
    assert response2 == []
