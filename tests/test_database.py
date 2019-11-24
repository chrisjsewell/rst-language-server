from rst_lsp.analyse.main import create_sphinx_app, retrieve_namespace
from rst_lsp.database.tinydb import Database


def test_update_conf_file(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    app_env = create_sphinx_app()
    roles, directives = retrieve_namespace(app_env)
    database.update_conf_file("conf.py", roles, directives)
    assert len(database._tbl_classes) == 181
    assert database.query_role("index") == {
        "element": "role",
        "name": "index",
        "description": "",
        "module": "sphinx.roles",
    }
    assert database.query_role("py:func") == {
        "element": "role",
        "name": "py:func",
        "description": "",
        "module": "sphinx.domains.python",
    }
    assert database.query_directive("code") == {
        "element": "directive",
        "name": "code",
        "description": (
            "Parse and mark up content of a code block.\n\n"
            "This is compatible with docutils' :rst:dir:`code` directive."
        ),
        "klass": "sphinx.directives.patches.Code",
        "required_arguments": 0,
        "optional_arguments": 1,
        "has_content": True,
        "options": {
            "class": "class_option",
            "force": "flag",
            "name": "unchanged",
            "number-lines": "optional_int",
        },
    }
    database.update_conf_file("conf.py", {}, {})
    assert len(database._tbl_classes) == 0


def test_update_doc_lint(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    database._update_doc_lint(
        "test.rst",
        [
            {
                "line": 20,
                "type": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "sdf".',
            },
            {
                "line": 26,
                "type": "ERROR",
                "level": 3,
                "description": (
                    'Unknown directive type "dsfsdf".'
                    "\n\n.. dsfsdf::\n\n    import a\n"
                ),
            },
            {
                "line": 37,
                "type": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "sdf".',
            },
            {
                "line": 37,
                "type": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "abcf".',
            },
        ],
    )
    assert len(database._tbl_linting) == 4


def test_update_doc_elements(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    database._update_doc_elements(
        "test.rst",
        [
            {
                "lineno": 5,
                "start_char": 0,
                "level": 1,
                "length": 46,
                "element": "SectionElement",
            },
            {
                "lineno": 18,
                "start_char": 0,
                "raw": "`<sdf>`__",
                "alias": "sdf",
                "ref_type": "anonymous",
                "alt_text": "",
                "element": "LinkElement",
            },
        ],
    )
    assert len(database._tbl_elements) == 2
    database._update_doc_elements(
        "test.rst",
        [
            {
                "lineno": 5,
                "start_char": 0,
                "level": 1,
                "length": 46,
                "element": "SectionElement",
            },
        ],
    )
    assert len(database._tbl_elements) == 1
