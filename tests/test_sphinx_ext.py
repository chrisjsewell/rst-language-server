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


def test_basic_doctree(get_test_file_content, file_regression):
    content = get_test_file_content("test_basic.rst")
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(content, app_env)
    file_regression.check(results.doctree.pformat())


def test_basic_linting(get_test_file_content, data_regression):
    content = get_test_file_content("test_basic.rst")
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(content, app_env)
    # TODO inline errors from docutils refers to wrong line, if after line break
    data_regression.check(results.linting)


def test_basic_database(get_test_file_content, data_regression):
    content = get_test_file_content("test_basic.rst")
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(content, app_env)
    data_regression.check(
        {
            "positions": results.positions,
            "references": results.references,
            "targets": results.targets,
            "linting": results.linting,
        }
    )


def test_lint_severe(get_test_file_content, data_regression):
    content = get_test_file_content("test_lint_severe.rst")
    app_env = create_sphinx_app()
    results = assess_source(content, app_env)
    data_regression.check(
        {
            "positions": results.positions,
            "references": results.references,
            "targets": results.targets,
            "linting": results.linting,
        }
    )


def test_section_levels(get_test_file_content, data_regression):
    content = get_test_file_content("test_sections.rst")
    app_env = create_sphinx_app()
    results = assess_source(content, app_env)
    data_regression.check(
        {
            "positions": results.positions,
            "references": results.references,
            "targets": results.targets,
            "linting": results.linting,
        }
    )


def test_sphinx_elements(file_regression, data_regression):
    from textwrap import dedent

    source = dedent(
        """\
        .. _title:

        Title
        -----

        :ref:`title`
        :ref:`fig1`
        :ref:`tbl1`
        :eq:`eq1`
        :numref:`code1`
        :cite:`citation`
        :unknown:`abc`

        .. versionadded:: 1.0

            A note about |RST|

        .. figure:: abc.png
           :name: fig1

        .. table:: Truth table for "not"
            :widths: auto
            :name: tbl1

            =====  =====
            A      not A
            =====  =====
            False  True
            True   False
            =====  =====

        .. math::
            :nowrap:
            :label: eq1

            \\begin{eqnarray}
                y    & = & ax^2 + bx + c \\\\
                f(x) & = & x^2 + 2xy + y^2
            \\end{eqnarray}

        .. code-block:: python::
            :name: code1

            pass

        .. |RST| replace:: ReStructuredText
        """
    )
    app_env = create_sphinx_app(confoverrides={"extensions": ["sphinxcontrib.bibtex"]})
    results = assess_source(source, app_env)
    file_regression.check(results.doctree.pformat())
    data_regression.check(
        {
            "lints": results.linting,
            "positions": results.positions,
            "references": results.references,
            "pending_xrefs": results.pending_xrefs,
            "targets": results.targets,
        }
    )
