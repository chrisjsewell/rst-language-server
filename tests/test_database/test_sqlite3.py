import pytest

from rst_lsp.database.sqllite3 import Database
from rst_lsp.sphinx_ext.main import create_sphinx_app, retrieve_namespace


@pytest.fixture(scope="function")
def open_db():
    db = Database()
    with db:
        yield db


def test_init(open_db, data_regression):
    data_regression.check(open_db.to_json())


def test_update_conf_file(open_db, data_regression):
    app_env = create_sphinx_app()
    roles, directives = retrieve_namespace(app_env)
    open_db.update_conf_file("conf.py", roles, directives)
    open_db.update_conf_file("conf.py", roles, directives)
    assert (
        open_db.cursor.execute("SELECT Count() FROM documents").fetchone()["Count()"]
        == 1
    )
    data_regression.check(
        {
            "conf_file": open_db.query_conf_file(),
            "directive": open_db.query_directive("container"),
            "role": open_db.query_role("index"),
            "directives": next(open_db.query_directives(["container"])),
            "roles": next(open_db.query_roles(["index"])),
        }
    )


def test_update_doc(open_db, data_regression):
    open_db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[{}],
        lints=[],
    )
    open_db.update_doc(
        uri="test.rst",
        positions=[
            {
                "block": True,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_7",
            }
        ],
        doc_symbols=[{"children": []}],
        lints=[
            {
                "source": "docutils",
                "line": 20,
                "type": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "sdf".',
            }
        ],
        references=[
            {
                "position_uuid": "uuid_1",
                "node": "substitution_reference",
                "classes": [],
                "same_doc": True,
                "reference": "uuid_3",
            },
        ],
        targets=[
            {
                "position_uuid": "uuid_4",
                "node": "substitution_definition",
                "classes": [],
                "target": "uuid_3",
            }
        ],
    )
    data_regression.check(open_db.to_json())


def test_query_doc(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    assert open_db.query_doc("test.rst") == {
        "dtype": "rst",
        "mtime": None,
        "uri": "test.rst",
    }
    assert list(open_db.query_docs()) == [
        {"dtype": "rst", "mtime": None, "uri": "test.rst"}
    ]


def test_query_doc_symbols(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[{"children": []}],
        lints=[],
    )
    assert open_db.query_doc_symbols("test.rst") == [{"children": []}]


def test_query_lint(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[
            {
                "source": "docutils",
                "line": 20,
                "type": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "sdf".',
            }
        ],
    )
    assert list(open_db.query_lint("test.rst")) == [
        {
            "uri": "test.rst",
            "source": "docutils",
            "line": 20,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "sdf".',
        }
    ]


def test_query_position_uuid(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[
            {
                "block": True,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_7",
            }
        ],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    assert open_db.query_position_uuid("uuid_7") == {
        "uuid": "uuid_7",
        "uri": "test.rst",
        "parent_uuid": None,
        "block": True,
        "type": "hyperlink_target",
        "title": "hyperlink_target",
        "startLine": 0,
        "startCharacter": 0,
        "endLine": 0,
        "endCharacter": 9,
        "level": None,
        "rtype": None,
        "dtype": None,
        "contentLine": None,
        "contentIndent": None,
        "klass": None,
        "arguments": None,
        "options": None,
    }


def test_query_positions(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[
            {
                "block": True,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_1",
            },
            {
                "block": False,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_2",
            },
        ],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    assert list(open_db.query_positions(uri=("test.rst", "testx.rst"), block=True)) == [
        {
            "uuid": "uuid_1",
            "uri": "test.rst",
            "parent_uuid": None,
            "block": True,
            "type": "hyperlink_target",
            "title": "hyperlink_target",
            "startLine": 0,
            "startCharacter": 0,
            "endLine": 0,
            "endCharacter": 9,
            "level": None,
            "rtype": None,
            "dtype": None,
            "contentLine": None,
            "contentIndent": None,
            "klass": None,
            "arguments": None,
            "options": None,
        }
    ]


def test_query_at_position(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[
            {
                "block": False,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_2",
            },
            {
                "block": True,
                "endCharacter": 9,
                "endLine": 3,
                "parent_uuid": None,
                "startCharacter": 5,
                "startLine": 1,
                "title": "hyperlink_target",
                "type": "hyperlink_target",
                "uuid": "uuid_1",
            },
        ],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    assert open_db.query_at_position(uri="test.rst", line=4, character=6) is None
    assert open_db.query_at_position(uri="test.rst", line=2, character=6) == {
        "uri": "test.rst",
        "block": True,
        "endCharacter": 9,
        "endLine": 3,
        "parent_uuid": None,
        "startCharacter": 5,
        "startLine": 1,
        "title": "hyperlink_target",
        "type": "hyperlink_target",
        "uuid": "uuid_1",
        "level": None,
        "rtype": None,
        "dtype": None,
        "contentLine": None,
        "contentIndent": None,
        "klass": None,
        "arguments": None,
        "options": None,
    }


def test_query_definitions(open_db):
    open_db.update_doc(
        uri="test.rst",
        positions=[],
        doc_symbols=[{"children": []}],
        lints=[],
        references=[
            {
                "position_uuid": "uuid_1",
                "node": "substitution_reference",
                "classes": ["a"],
                "same_doc": True,
                "reference": "uuid_5",
            },
            {
                "position_uuid": "uuid_1",
                "node": "substitution_reference",
                "classes": ["g"],
                "same_doc": True,
                "reference": "uuid_7",
            },
            {
                "position_uuid": "uuid_2",
                "node": "substitution_reference",
                "classes": ["b"],
                "same_doc": True,
                "reference": "uuid_6",
            },
        ],
        targets=[
            {
                "position_uuid": "uuid_3",
                "node": "substitution_definition",
                "classes": ["c"],
                "target": "uuid_5",
            },
            {
                "position_uuid": "uuid_4",
                "node": "substitution_definition",
                "classes": ["d"],
                "target": "uuid_6",
            },
        ],
    )
    assert list(open_db.query_definitions(uri="test.rst", position_uuid="uuid_1")) == [
        {
            "target": "uuid_5",
            "uri": "test.rst",
            "position_uuid": "uuid_3",
            "node": "substitution_definition",
            "classes": ["c"],
        }
    ]
