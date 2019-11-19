import os

import pytest


PATH = os.path.realpath(os.path.join(os.path.dirname(__file__), "raw_files"))


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
