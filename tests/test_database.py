from rst_lsp.parser import init_sphinx
from rst_lsp.database import Database


def test_update_classes(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    with init_sphinx(confdir=None, confoverrides=None) as sphinx_init:
        database.update_classes(sphinx_init.roles, sphinx_init.directives)
    assert len(database.tbl_global) == 181
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
        "class": "sphinx.directives.patches.Code",
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
    database.update_classes({}, {})
    assert len(database.tbl_global) == 0


def test_update_doc_lint(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    database.update_doc_lint(
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
    assert len(database.tbl_linting) == 4


def test_update_doc_elements(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    database.update_doc_elements(
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
    assert len(database.tbl_elements) == 2
    database.update_doc_elements(
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
    assert len(database.tbl_elements) == 1
