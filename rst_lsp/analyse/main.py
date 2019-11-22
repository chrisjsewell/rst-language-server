"""Module for building a mapping of document/line/character to RST elements.

This modules contains `init_sphinx`,
which is a context manager, that allows sphinx to be initialised,
outside of the command-line, and also collects all available roles and directives.

"""
# TODO improve efficiency for multiple calls, e.g. by caching (using lru_cache?)
# TODO subclass Sphinx, so we can only initialise the parts we require.
from contextlib import contextmanager
from collections import namedtuple
import copy
from io import StringIO
from importlib import import_module
import locale
import os
import shutil
import tempfile
from typing import List

import attr

from docutils.nodes import document
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser as RSTParser

from sphinx import package_dir
import sphinx.locale
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.util.console import nocolor, color_terminal, terminal_safe  # noqa
from sphinx.util.docutils import docutils_namespace, patch_docutils
from sphinx.util.docutils import sphinx_domains

from rst_lsp.docutils_ext.parser import parse_source
from rst_lsp.docutils_ext.reporter import new_document
from rst_lsp.docutils_ext.visitor import DocInfoVisitor

sphinx_init = namedtuple(
    "sphinx_init", ["env", "directives", "roles", "log_status", "log_warnings"]
)


@contextmanager
def init_sphinx(
    confdir=None, confoverrides=None, source_dir=None, output_dir=None
) -> sphinx_init:
    """Yield a Sphinx Application, within a context.

    This context implements the standard sphinx patches to docutils,
    including the addition of builtin and extension roles and directives.
    """

    # below is taken from sphinx.cmd.build.main
    # note: this may be removed in future
    sphinx.locale.setlocale(locale.LC_ALL, "")
    sphinx.locale.init_console(os.path.join(package_dir, "locale"), "sphinx")

    # below is adapted from sphinx.cmd.build.build_main
    confdir = confdir
    confoverrides = confoverrides or {}

    builder = "html"
    # TODO this is not efficient, to create temp directories on every call
    # these are not needed before build, but there existence is checked in ``Sphinx```
    sourcedir = source_dir or tempfile.mkdtemp()  # path to documentation source files
    # path for the cached environment and doctree
    # note source directory and destination directory cannot be identical
    doctreedir = outputdir = output_dir or tempfile.mkdtemp()

    app = None
    try:
        log_stream_status = StringIO()
        log_stream_warning = StringIO()
        with patch_docutils(confdir), docutils_namespace():

            from docutils.parsers.rst.directives import _directives, _directive_registry
            from docutils.parsers.rst.roles import _roles, _role_registry

            # regarding the ``_roles`` and ``_directives`` mapping;
            # sphinx presumably checks loads all roles/directives,
            # when it loads its internal and conf specified extensions,
            # however, docutils loads them on a lazy basis, when they are required
            # the _role_registry contains all docutils roles by their 'canonical' names,
            # but these are also mapped to language-dependent dependant names
            # in docutils.parsers.rst.roles.role and
            # similarly in docutils.parsers.rst.directives.directive
            # TODO work out how to obtain the correct language mapping
            # from docutils.languages import get_language

            app = Sphinx(
                sourcedir,
                confdir,
                outputdir,
                doctreedir,
                builder,
                confoverrides=confoverrides,
                status=log_stream_status,
                warning=log_stream_warning,
                # originally parsed
                # args.freshenv, args.warningiserror,
                # args.tags, args.verbosity, args.jobs, args.keep_going
            )
            # app.build(args.force_all, filenames)

            all_roles = copy.copy(_role_registry)
            all_roles.update(_roles)
            all_directives = copy.copy(_directives)
            for key, (modulename, classname) in _directive_registry.items():
                if key not in all_directives:
                    try:
                        module = import_module(
                            f"docutils.parsers.rst.directives.{modulename}"
                        )
                        all_directives[key] = getattr(module, classname)
                    except (AttributeError, ModuleNotFoundError):
                        pass
            for domain_name in app.env.domains:
                domain = app.env.get_domain(domain_name)
                prefix = "" if domain.name == "std" else f"{domain.name}:"
                # TODO 'default_domain' is also looked up by
                # sphinx.util.docutils.sphinx_domains.lookup_domain_element
                for role_name, role in domain.roles.items():
                    all_roles[f"{prefix}{role_name}"] = role
                for direct_name, direct in domain.directives.items():
                    all_roles[f"{prefix}{direct_name}"] = direct

            with sphinx_domains(app.env):
                # note this with statement redirects docutils role/directive getters,
                # to include loading from domains
                yield sphinx_init(
                    app.env,
                    all_directives,
                    all_roles,
                    log_stream_status.getvalue(),
                    log_stream_warning.getvalue(),
                )
    except (Exception, KeyboardInterrupt) as exc:
        # handle_exception(app, args, exc, error)
        raise exc
    finally:
        if not source_dir:
            shutil.rmtree(sourcedir, ignore_errors=True)
        if not output_dir:
            shutil.rmtree(outputdir, ignore_errors=True)


@attr.s
class SourceAssessResult:
    doctree: document = attr.ib()
    environment: BuildEnvironment = attr.ib()
    roles: dict = attr.ib()
    directives: dict = attr.ib()
    elements: List[dict] = attr.ib()
    linting: List[dict] = attr.ib()


def assess_source(
    content: str,
    filename: str = "input.rst",
    confdir: str = None,
    confoverrides: dict = None,
) -> SourceAssessResult:
    """Assess the content of an file.

    Parameters
    ----------
    content : str
        the content of the file
    filename : str
        the file path
    confdir : str or None
        path where configuration file (conf.py) is located
    confoverrides : dict or None
        dictionary containing parameters that will update those set from conf.py

    Returns
    -------
    SourceAssessResult

    """
    with init_sphinx(confdir=confdir, confoverrides=confoverrides) as sphinx_init:

        # TODO maybe sub-class sphinx.io.SphinxStandaloneReader?
        # (see also sphinx.testing.restructuredtext.parse, for a basic implementation)

        settings = OptionParser(components=(RSTParser,)).get_default_values()
        sphinx_init.env.prepare_settings(filename)
        settings.env = sphinx_init.env
        doc_warning_stream = StringIO()
        settings.warning_stream = doc_warning_stream
        settings.report_level = 2  # warning

        document, reporter = new_document(content, settings=settings)

        parse_source(content, document)

        visitor = DocInfoVisitor(document, content)
        document.walk(visitor)
        elements = visitor.info_datas[:]

    return SourceAssessResult(
        document,
        # TODO what can we extract data from environment to use in the database?
        sphinx_init.env,
        sphinx_init.roles,
        sphinx_init.directives,
        elements,
        # TODO should also capture additional formatting warnings,
        # like trailing whitespace, final newline, etc (look at doc8)
        reporter.log_capture,
    )

    # from docutils.parsers.rst import states
    # for state in states.state_classes:
    #     print(state)
