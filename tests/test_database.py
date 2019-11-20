from rst_lsp.database import Database


def test_update_classes(tmp_path):
    database = Database(str(tmp_path / "db.json"))
    database.update_classes()
    assert len(database.tbl_global) == 54
    assert database.query_role("index") == {
        "element": "role",
        "name": "index",
        "description": "",
        "module": "sphinx.roles",
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
