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
            "line": 51,
            "type": "WARNING",
            "level": 2,
            "description": (
                'Substitution definition "REF4" empty or invalid.\n\n'
                ".. |REF4| replace: bad syntax"
            ),
        },
    ]


def test_1_block_objects(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )

    objs = []
    for obj in results.block_objects:
        dct = attr.asdict(obj)
        dct.pop("parent", None)
        dct["element"] = obj.__class__.__name__
        objs.append(dct)
    # print(objs)
    assert objs == [
        {
            "lineno": 5,
            "start_char": 0,
            "level": 1,
            "length": 46,
            "element": "SectionElement",
        },
        {
            "lineno": 6,
            "start_char": 0,
            "arguments": ["html"],
            "options": {},
            "klass": "sphinx.directives.other.Only",
            "element": "DirectiveElement",
        },
        {
            "lineno": 9,
            "start_char": 4,
            "arguments": [],
            "options": {},
            "klass": "docutils.parsers.rst.directives.admonitions.Note",
            "element": "DirectiveElement",
        },
        {
            "lineno": 12,
            "start_char": 0,
            "arguments": ["python"],
            "options": {"linenos": None},
            "klass": "sphinx.directives.code.CodeBlock",
            "element": "DirectiveElement",
        },
        {
            "lineno": 21,
            "start_char": 0,
            "level": 2,
            "length": 30,
            "element": "SectionElement",
        },
        {
            "lineno": 25,
            "start_char": 0,
            "arguments": [],
            "options": {},
            "klass": "docutils.parsers.rst.directives.admonitions.Note",
            "element": "DirectiveElement",
        },
        {
            "lineno": 31,
            "start_char": 0,
            "level": 1,
            "length": 20,
            "element": "SectionElement",
        },
        {
            "lineno": 47,
            "start_char": 0,
            "arguments": ["file.png"],
            "options": {"alt": "REF1", "uri": "file.png"},
            "klass": "docutils.parsers.rst.directives.images.Image",
            "element": "DirectiveElement",
        },
        {
            "lineno": 48,
            "start_char": 0,
            "arguments": [],
            "options": {},
            "klass": "docutils.parsers.rst.directives.misc.Replace",
            "element": "DirectiveElement",
        },
    ]


def test_1_inline_objects(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )

    objs = []
    for obj in results.inline_objects:
        dct = attr.asdict(obj)
        dct.pop("parent", None)
        dct["element"] = obj.__class__.__name__
        objs.append(dct)
    # import pprint
    # pprint.pprint(objs)
    assert objs == [
        {
            "lineno": 18,
            "start_char": 0,
            "raw": "`<sdf>`__",
            "alias": "sdf",
            "ref_type": "anonymous",
            "alt_text": "",
            "element": "LinkElement",
        },
        {
            "lineno": 23,
            "start_char": 0,
            "raw": "`<http://www.python.org/>`_",
            "alias": "http://www.python.org/",
            "ref_type": "standard",
            "alt_text": "",
            "element": "LinkElement",
        },
        {
            "lineno": 27,
            "start_char": 12,
            "raw": "`a link to python <www.python.org>`_",
            "alias": "www.python.org",
            "ref_type": "standard",
            "alt_text": "a link to python",
            "element": "LinkElement",
        },
        {
            "lineno": 28,
            "start_char": 4,
            "raw": ":sdf:`asdasx`",
            "role": "sdf",
            "content": "asdasx",
            "element": "RoleElement",
        },
        {
            "lineno": 37,
            "start_char": 0,
            "raw": ":cite:`sadasd`",
            "role": "cite",
            "content": "sadasd",
            "element": "RoleElement",
        },
        {
            "lineno": 38,
            "start_char": 0,
            "raw": ":cite:`asd`",
            "role": "cite",
            "content": "asd",
            "element": "RoleElement",
        },
        {
            "lineno": 44,
            "start_char": 0,
            "raw": ":sdf:`saasf`",
            "role": "sdf",
            "content": "saasf",
            "element": "RoleElement",
        },
        {
            "lineno": 44,
            "start_char": 14,
            "raw": ":abcf:`saasf`",
            "role": "abcf",
            "content": "saasf",
            "element": "RoleElement",
        },
    ]


# def test_doctest():
#     results = assess_source(
#         # ".. _sdf:",
#         ":ref:`~sdf.dsf`",
#         confoverrides={"extensions": ["sphinxcontrib.bibtex"]},
#     )
#     print(results.errors)
#     print(type(results.doctree.children[0].children[0]))
#     raise
