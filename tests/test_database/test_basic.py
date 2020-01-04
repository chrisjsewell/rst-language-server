from datetime import datetime

from rst_lsp.database.main import DocutilsCache
from rst_lsp.sphinx_ext.main import create_sphinx_app, retrieve_namespace


def test_init(tmp_path, data_regression):
    cache = DocutilsCache(str(tmp_path), echo=False)
    data_regression.check(cache.to_dict())


def test_update_conf_file(tmp_path, data_regression):
    cache = DocutilsCache(str(tmp_path), echo=False)
    app_env = create_sphinx_app()
    roles, directives = retrieve_namespace(app_env)
    cache.update_conf_file(
        "conf.py",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        roles=roles,
        directives=directives,
    )
    cache.update_conf_file(
        "conf.py",
        mtime=datetime(2019, 12, 30, 0, 0, 1),
        roles=roles,
        directives=directives,
    )
    data_regression.check(
        cache.to_dict(order_by={"roles": "name", "directives": "name"})
    )


def test_update_doc(tmp_path, data_regression):
    cache = DocutilsCache(str(tmp_path), echo=False)
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[{}],
        lints=[],
    )
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 1),
        positions=[
            {
                "uuid": "uuid_1",
                "block": True,
                "endCharacter": 9,
                "endLine": 0,
                "parent_uuid": None,
                "startCharacter": 0,
                "startLine": 0,
                "title": "hyperlink_target",
                "category": "hyperlink_target",
            }
        ],
        doc_symbols=[{"children": []}],
        lints=[
            {
                "source": "docutils",
                "line": 20,
                "category": "ERROR",
                "level": 3,
                "description": 'Unknown interpreted text role "sdf".',
            }
        ],
        targets=[
            {
                "uuid": "uuid_2",
                "position_uuid": "uuid_1",
                "node_type": "substitution_definition",
                "classes": [],
            }
        ],
        references=[
            {
                "position_uuid": "uuid_1",
                "target_uuid": "uuid_2",
                "node_type": "substitution_reference",
                "classes": [],
                # "same_doc": True,
            },
        ],
    )
    data_regression.check(cache.to_dict())


def test_query_doc(tmp_path):
    cache = DocutilsCache(str(tmp_path), echo=False)
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[{"contents": []}],
        lints=[],
    )
    doc = cache.query_doc("test.rst")
    assert doc.column_dict() == {
        "pk": 1,
        "mtime": datetime(2019, 12, 30, 0, 0, 0),
        "uri": "test.rst",
        "symbols": [{"contents": []}],
    }


def test_query_doc_load_lints(tmp_path):
    cache = DocutilsCache(str(tmp_path), echo=False)
    lint = {
        "source": "docutils",
        "line": 20,
        "category": "ERROR",
        "level": 3,
        "description": 'Unknown interpreted text role "sdf".',
    }
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        positions=[],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[lint],
    )
    doc = cache.query_doc("test.rst", load_lints=True)

    assert doc.lints[0].column_dict(drop=("pk",)) == lint


def test_query_doc_load_positions(tmp_path):
    cache = DocutilsCache(str(tmp_path), echo=False)
    position = {
        "block": True,
        "endCharacter": 9,
        "endLine": 0,
        "parent_uuid": None,
        "startCharacter": 0,
        "startLine": 0,
        "title": "hyperlink_target",
        "category": "hyperlink_target",
        "uuid": "uuid_1",
        "section_level": None,
        "role_name": None,
        "directive_name": None,
        "directive_data": None,
    }
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        positions=[position],
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    doc = cache.query_doc("test.rst", load_positions=True)

    assert doc.positions[0].column_dict(drop=("pk",)) == position


def test_query_at_position(tmp_path):
    cache = DocutilsCache(str(tmp_path), echo=False)
    positions = [
        {
            "uuid": "uuid_1",
            "startLine": 0,
            "startCharacter": 0,
            "endLine": 0,
            "endCharacter": 9,
            "block": False,
        },
        {
            "uuid": "uuid_2",
            "startLine": 1,
            "startCharacter": 5,
            "endLine": 3,
            "endCharacter": 9,
            "block": False,
        },
    ]
    cache.update_doc(
        uri="test.rst",
        mtime=datetime(2019, 12, 30, 0, 0, 0),
        positions=positions,
        references=[],
        targets=[],
        doc_symbols=[],
        lints=[],
    )
    assert cache.query_at_position(uri="test.rst", line=4, character=6) is None
    cache.query_at_position(uri="test.rst", line=0, character=6).uuid == "uuid_1"
    cache.query_at_position(uri="test.rst", line=2, character=6).uuid == "uuid_2"
