from rst_lsp.database.sqllite3 import Database
from rst_lsp.sphinx_ext.main import create_sphinx_app, retrieve_namespace


def test_init(data_regression):
    db = Database()
    data_regression.check(db.to_json())


def test_update_conf_file(data_regression):
    db = Database()
    app_env = create_sphinx_app()
    roles, directives = retrieve_namespace(app_env)
    db.update_conf_file("conf.py", roles, directives)
    db.update_conf_file("conf.py", roles, directives)
    assert db.cursor.execute("SELECT Count() FROM documents").fetchone()["Count()"] == 1
    data_regression.check(
        {
            "conf_file": db.query_conf_file(),
            "directive": db.query_directive("container"),
            "role": db.query_role("index"),
            "directives": next(db.query_directives(["container"])),
            "roles": next(db.query_roles(["index"])),
        }
    )


def test_update_doc(data_regression):
    db = Database()
    db.update_doc(
        uri="test.rst", positions=[], references=[], doc_symbols=[{}], lints=[],
    )
    db.update_doc(
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
        references=[],
    )
    data_regression.check(db.to_json())


def test_query_doc():
    db = Database()
    db.update_doc(
        uri="test.rst", positions=[], references=[], doc_symbols=[], lints=[],
    )
    assert db.query_doc("test.rst") == {
        "dtype": "rst",
        "mtime": None,
        "uri": "test.rst",
    }
    assert list(db.query_docs()) == [{"dtype": "rst", "mtime": None, "uri": "test.rst"}]


def test_query_doc_symbols():
    db = Database()
    db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
        doc_symbols=[{"children": []}],
        lints=[],
    )
    assert db.query_doc_symbols("test.rst") == [{"children": []}]


def test_query_lint():
    db = Database()
    db.update_doc(
        uri="test.rst",
        positions=[],
        references=[],
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
    assert list(db.query_lint("test.rst")) == [
        {
            "uri": "test.rst",
            "source": "docutils",
            "line": 20,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "sdf".',
        }
    ]


def test_query_position_uuid():
    db = Database()
    db.update_doc(
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
        doc_symbols=[],
        lints=[],
    )
    assert db.query_position_uuid("uuid_7") == {
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
