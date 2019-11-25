import os
from unittest import mock
import uuid

import pytest


PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), "raw_files"))
TEST_UUIDS = ["uuid_{}".format(i) for i in range(10000)]


@pytest.fixture(autouse=True)
def mock_uuid():
    with mock.patch.object(uuid, "uuid4", side_effect=TEST_UUIDS):
        yield


@pytest.fixture()
def get_test_file_path():
    def _get_test_file_path(name):
        return os.path.join(PATH, name)

    return _get_test_file_path


@pytest.fixture()
def get_test_file_content(get_test_file_path):
    def _get_test_file_content(name):
        with open(get_test_file_path(name)) as handle:
            content = handle.read()
        return content

    return _get_test_file_content


@pytest.fixture()
def temp_cwd(tmp_path):
    original_path = os.getcwd()
    os.chdir(str(tmp_path))
    yield tmp_path
    os.chdir(original_path)
