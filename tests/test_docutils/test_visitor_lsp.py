from textwrap import dedent

from docutils import frontend, utils
from docutils.parsers import rst

from rst_lsp.docutils_ext.inliner_lsp import InlinerLSP
from rst_lsp.docutils_ext.block_lsp import RSTParserCustom
from rst_lsp.docutils_ext.visitor_lsp import VisitorLSP


def run_parser(source, parser_class):
    inliner = InlinerLSP(doc_text=source)
    parser = parser_class(inliner=inliner)
    option_parser = frontend.OptionParser(components=(rst.Parser,))
    settings = option_parser.get_default_values()
    settings.report_level = 5
    settings.halt_level = 5
    # settings.debug = package_unittest.debug
    document = utils.new_document("test data", settings)
    parser.parse(source, document)
    return document


def test_inline_mixed(data_regression):
    source = dedent(
        """\
    [citation]_ |sub| ref_ `embed <ref_>`_ :title:`a`
    anonymous__
    _`inline-target`
    [1]_ [#]_ [*]_
    """
    )
    document = run_parser(source, parser_class=RSTParserCustom)
    visitor = VisitorLSP(document, source)
    document.walkabout(visitor)
    data_regression.check(
        {
            "db_entries": visitor.db_entries,
            "doc_symbols": visitor.nesting.document_symbols,
        }
    )


def test_sections(data_regression):
    source = dedent(
        """\
    title
    =====

    :title:`a`

    sub-title
    ---------

    :title:`b`

    sub-title2
    ----------

    :title:`c`

    sub-sub-title
    ~~~~~~~~~~~~~

    :title:`d`

    title2
    ======

    :title:`e`
    """
    )
    document = run_parser(source, parser_class=RSTParserCustom)
    visitor = VisitorLSP(document, source)
    document.walkabout(visitor)
    data_regression.check(
        {
            "db_entries": visitor.db_entries,
            "doc_symbols": visitor.nesting.document_symbols,
        }
    )


def test_explicits(data_regression):
    source = dedent(
        """\
    .. _target:

    [1]_ target_ |symbol| [cite]_

    .. [1] This is a footnote.
    .. |symbol| image:: symbol.png
    .. [cite] This is a citation.
    """
    )
    document = run_parser(source, parser_class=RSTParserCustom)
    visitor = VisitorLSP(document, source)
    document.walkabout(visitor)
    data_regression.check(
        {
            "db_entries": visitor.db_entries,
            "doc_symbols": visitor.nesting.document_symbols,
        }
    )


def test_directives(data_regression):
    source = dedent(
        """\
    .. code:: python

       a=1

    .. image:: abc.png
    """
    )
    document = run_parser(source, parser_class=RSTParserCustom)
    visitor = VisitorLSP(document, source)
    document.walkabout(visitor)
    data_regression.check(
        {
            "db_entries": visitor.db_entries,
            "doc_symbols": visitor.nesting.document_symbols,
        }
    )


def test_mixed1(data_regression):
    source = dedent(
        """\
    .. _target:

    title
    -----

    .. note::

       [1]_ target_ |symbol| [cite]_

    .. [1] This is a footnote.
    .. |symbol| image:: symbol.png
    .. [cite] This is a citation.
    """
    )
    document = run_parser(source, parser_class=RSTParserCustom)
    visitor = VisitorLSP(document, source)
    document.walkabout(visitor)
    data_regression.check(
        {
            "db_entries": visitor.db_entries,
            "doc_symbols": visitor.nesting.document_symbols,
        }
    )
