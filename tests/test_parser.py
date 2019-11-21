import attr

from rst_lsp.parser import assess_source


def test_1_roles(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    # print(sorted(results.roles.keys()))
    assert set(results.roles.keys()) == {
        "abbr",
        "abbreviation",
        "acronym",
        "anonymous-reference",
        "any",
        "c:data",
        "c:func",
        "c:function",
        "c:macro",
        "c:member",
        "c:type",
        "c:var",
        "citation-reference",
        "cite",
        "cmdoption",
        "code",
        "command",
        "cpp:alias",
        "cpp:any",
        "cpp:class",
        "cpp:concept",
        "cpp:enum",
        "cpp:enum-class",
        "cpp:enum-struct",
        "cpp:enumerator",
        "cpp:expr",
        "cpp:func",
        "cpp:function",
        "cpp:member",
        "cpp:namespace",
        "cpp:namespace-pop",
        "cpp:namespace-push",
        "cpp:struct",
        "cpp:texpr",
        "cpp:type",
        "cpp:union",
        "cpp:var",
        "dfn",
        "doc",
        "download",
        "emphasis",
        "envvar",
        "eq",
        "file",
        "footnote-reference",
        "glossary",
        "guilabel",
        "index",
        "js:attr",
        "js:attribute",
        "js:class",
        "js:data",
        "js:func",
        "js:function",
        "js:meth",
        "js:method",
        "js:mod",
        "js:module",
        "kbd",
        "keyword",
        "literal",
        "mailheader",
        "makevar",
        "manpage",
        "math",
        "math:numref",
        "menuselection",
        "mimetype",
        "named-reference",
        "newsgroup",
        "numref",
        "option",
        "pep",
        "pep-reference",
        "productionlist",
        "program",
        "py:attr",
        "py:attribute",
        "py:class",
        "py:classmethod",
        "py:const",
        "py:currentmodule",
        "py:data",
        "py:decorator",
        "py:decoratormethod",
        "py:exc",
        "py:exception",
        "py:func",
        "py:function",
        "py:meth",
        "py:method",
        "py:mod",
        "py:module",
        "py:obj",
        "py:staticmethod",
        "raw",
        "ref",
        "regexp",
        "restructuredtext-unimplemented-role",
        "rfc",
        "rfc-reference",
        "rst:dir",
        "rst:directive",
        "rst:directive:option",
        "rst:role",
        "samp",
        "strong",
        "subscript",
        "substitution-reference",
        "superscript",
        "target",
        "term",
        "title-reference",
        "token",
        "uri-reference",
    }


def test_1_directives(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    # print(sorted(results.directives.keys()))
    assert set(results.directives.keys()) == {
        "acks",
        "admonition",
        "attention",
        "bibliography",
        "caution",
        "centered",
        "class",
        "code",
        "code-block",
        "codeauthor",
        "compound",
        "container",
        "contents",
        "cssclass",
        "csv-table",
        "danger",
        "date",
        "default-domain",
        "default-role",
        "deprecated",
        "describe",
        "epigraph",
        "error",
        "figure",
        "footer",
        "header",
        "highlight",
        "highlightlang",
        "highlights",
        "hint",
        "hlist",
        "image",
        "important",
        "include",
        "index",
        "line-block",
        "list-table",
        "literalinclude",
        "math",
        "meta",
        "moduleauthor",
        "note",
        "object",
        "only",
        "parsed-literal",
        "pull-quote",
        "raw",
        "replace",
        "restructuredtext-test-directive",
        "role",
        "rst-class",
        "rubric",
        "sectionauthor",
        "sectnum",
        "seealso",
        "sidebar",
        "sourcecode",
        "table",
        "tabularcolumns",
        "target-notes",
        "tip",
        "title",
        "toctree",
        "topic",
        "unicode",
        "versionadded",
        "versionchanged",
        "warning",
    }


def test_1_errors(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    # print(results.errors)
    # TODO inline errors may refer to wrong line, if there a line breaks
    assert results.errors == [
        {
            "line": 27,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "sdf".',
        },
        {
            "line": 33,
            "type": "ERROR",
            "level": 3,
            "description": (
                'Unknown directive type "dsfsdf".\n\n.. dsfsdf::\n\n    import a\n'
            ),
        },
        {
            "line": 44,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "sdf".',
        },
        {
            "line": 44,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "abcf".',
        },
        {
            "line": 53,
            "type": "WARNING",
            "level": 2,
            "description": (
                'Substitution definition "REF4" empty or invalid.\n\n'
                ".. |REF4| replace: bad syntax"
            ),
        },
    ]


def test_1_elements(get_test_file_content, data_regression):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    data_regression.check(results.elements)


def test_doctest():
    results = assess_source(
        """\
.. _sdf:

:ref:`zffx`

a headerlink_

|A|
""",
        confoverrides={"extensions": ["sphinxcontrib.bibtex"]},
    )
    print(results.errors)
    print(results.doctree.pformat())
    # raise
