from rst_lsp.analyse.main import assess_source


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


def test_1_linting(get_test_file_content, data_regression):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    # TODO inline errors from docutils refers to wrong line, if after line break
    data_regression.check(results.linting)


def test_1_elements(get_test_file_content, data_regression):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    data_regression.check(results.elements)


def test_doctest(data_regression):
    # NOTE this is used in example in rst_lsp.analyse example
    from textwrap import dedent

    source = dedent(
        """\
        .. _title:

        Title
        -----

        :ref:`title`
        :cite:`citation`
        :unknown:`abc`

        .. versionadded:: 1.0

            A note about |RST|

        .. |RST| replace:: ReStructuredText
        """
    )
    results = assess_source(
        source, confoverrides={"extensions": ["sphinxcontrib.bibtex"]},
    )
    # import pprint
    # pprint.pprint(results.linting)
    # pprint.pprint(results.elements)
    data_regression.check({"lints": results.linting, "elements": results.elements})
