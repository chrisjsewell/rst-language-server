import os
import sys

from docutils import frontend, utils
from docutils.parsers import rst
import pytest
import yaml

from rst_lsp.docutils_ext.inliner_pos import PositionInliner
from rst_lsp.docutils_ext.visitor_db import DatabaseVisitor


def load_yaml(path):
    with open(path) as fp:
        data = yaml.safe_load(fp)
    return data


def run_parser(case):
    source = "\n".join(case["in"])

    inliner = PositionInliner(doc_text=source)

    parser = rst.Parser(inliner=inliner)
    option_parser = frontend.OptionParser(components=(rst.Parser,))
    settings = option_parser.get_default_values()
    settings.report_level = 5
    settings.halt_level = 5
    # settings.debug = package_unittest.debug

    document = utils.new_document("test data", settings)
    parser.parse(source, document)
    return document


@pytest.mark.parametrize(
    "name,number,case",
    [
        (name, i, case)
        for name, cases in load_yaml(
            os.path.join(os.path.dirname(__file__), "inputs/test_visitor_db.yaml")
        ).items()
        for i, case in enumerate(cases)
    ],
)
def test_doc_position(name, number, case):
    document = run_parser(case)
    visitor = DatabaseVisitor(document, "\n".join(case["in"]))
    document.walkabout(visitor)
    try:
        assert case["out"] == visitor.db_entries
    except AssertionError:
        yaml.dump(visitor.db_entries, sys.stdout, default_flow_style=False)
        raise
