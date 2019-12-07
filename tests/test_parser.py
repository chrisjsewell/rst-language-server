from rst_lsp.sphinx_ext.main import assess_source
from rst_lsp.sphinx_ext.main import create_sphinx_app, retrieve_namespace


def test_retrieve_namespace(data_regression):
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    roles, directives = retrieve_namespace(app_env)
    data_regression.check(
        {
            "roles": list(sorted(roles.keys())),
            "directives": list(sorted(directives.keys())),
        }
    )


def test_1_linting(get_test_file_content, data_regression):
    content = get_test_file_content("test1.rst")
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(content, app_env)
    # TODO inline errors from docutils refers to wrong line, if after line break
    data_regression.check(results.linting)


def test_1_elements(get_test_file_content, data_regression):
    content = get_test_file_content("test1.rst")
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(content, app_env)
    data_regression.check(results.elements)


def test_lint_severe(get_test_file_content, data_regression):
    content = get_test_file_content("test_lint_severe.rst")
    app_env = create_sphinx_app()
    results = assess_source(content, app_env)
    data_regression.check({"elements": results.elements, "linting": results.linting})


def test_section_levels(get_test_file_content, data_regression):
    content = get_test_file_content("test_sections.rst")
    app_env = create_sphinx_app()
    results = assess_source(content, app_env)
    data_regression.check({"elements": results.elements, "linting": results.linting})


def test_doctest(data_regression):
    # NOTE this is used in example in rst_lsp.sphinx_ext example
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
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(source, app_env)
    data_regression.check({"lints": results.linting, "elements": results.elements})
