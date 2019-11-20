from rst_lsp.parser import assess_source


def test_1_roles(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )

    assert set(results.roles.keys()) == {
        "command",
        "regexp",
        "makevar",
        "dfn",
        "manpage",
        "rfc",
        "pep",
        "index",
        "cite",
        "newsgroup",
        "guilabel",
        "mailheader",
        "download",
        "eq",
        "menuselection",
        "program",
        "any",
        "abbr",
        "mimetype",
        "file",
        "samp",
        "kbd",
    }


def test_1_directives(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    assert set(results.directives.keys()) == {
        "seealso",
        "hlist",
        "moduleauthor",
        "note",
        "sourcecode",
        "tabularcolumns",
        "sectionauthor",
        "cssclass",
        "versionadded",
        "meta",
        "literalinclude",
        "highlightlang",
        "rst-class",
        "deprecated",
        "code",
        "math",
        "bibliography",
        "codeauthor",
        "default-role",
        "figure",
        "code-block",
        "default-domain",
        "toctree",
        "object",
        "only",
        "csv-table",
        "versionchanged",
        "highlight",
        "describe",
        "centered",
        "include",
        "index",
        "acks",
        "list-table",
        "table",
    }


def test_1_errors(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    assert results.errors == [
        {
            "line": 2,
            "type": "INFO",
            "level": 1,
            "description": 'Duplicate explicit target name: "python".',
        },
        {
            "line": 20,
            "type": "INFO",
            "level": 1,
            "description": (
                'No role entry for "sdf" in module '
                '"docutils.parsers.rst.languages.en".\n'
                'Trying "sdf" as canonical role name.'
            ),
        },
        {
            "line": 20,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "sdf".',
        },
        {
            "line": 26,
            "type": "INFO",
            "level": 1,
            "description": (
                'No directive entry for "dsfsdf" in module '
                '"docutils.parsers.rst.languages.en".\n'
                'Trying "dsfsdf" as canonical directive name.'
            ),
        },
        {
            "line": 26,
            "type": "ERROR",
            "level": 3,
            "description": (
                'Unknown directive type "dsfsdf".' "\n\n.. dsfsdf::\n\n    import a\n"
            ),
        },
        {
            "line": 37,
            "type": "INFO",
            "level": 1,
            "description": (
                'No role entry for "sdf" in module '
                '"docutils.parsers.rst.languages.en".\n'
                'Trying "sdf" as canonical role name.'
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
            "type": "INFO",
            "level": 1,
            "description": (
                'No role entry for "abcf" in module '
                '"docutils.parsers.rst.languages.en".\n'
                'Trying "abcf" as canonical role name.'
            ),
        },
        {
            "line": 37,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "abcf".',
        },
    ]


def test_1_element_info(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    assert {k: len(v) for k, v in results.element_info.items()} == {
        "sections": 3,
        "directives": 4,
        "roles": 5,
    }
    assert {
        k: [e.__class__.__name__ for e in els] for k, els in results.line_lookup.items()
    } == {
        2: ["section_info"],
        3: ["directive_info"],
        6: ["directive_info"],
        9: ["directive_info"],
        16: ["section_info"],
        18: ["directive_info"],
        20: ["role_info"],
        24: ["section_info"],
        30: ["role_info", "role_info"],
        37: ["role_info", "role_info"],
    }


def test_1_environment(get_test_file_content):
    content = get_test_file_content("test1.rst")
    results = assess_source(
        content, confoverrides={"extensions": ["sphinxcontrib.bibtex"]}
    )
    print(results.environment.__dir__())
    raise
