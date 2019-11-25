"""Module for building a mapping of document/line/character to RST elements.

This modules contains `sphinx_env`,
which is a context manager, that allows sphinx to be initialised,
outside of the command-line.

"""
# TODO improve efficiency for multiple calls, e.g. by caching (using lru_cache?)
# TODO subclass Sphinx, so we can only initialise the parts we require.
from contextlib import contextmanager
import copy
from io import StringIO
from importlib import import_module
import locale
import os
import shutil
import tempfile
from typing import IO, List, Tuple

import attr

from docutils.nodes import document
from docutils.frontend import OptionParser
from docutils.parsers.rst import Parser as RSTParser
from docutils.utils import SystemMessage

from sphinx import package_dir
import sphinx.locale
from sphinx.application import Sphinx
from sphinx.util.console import nocolor, color_terminal, terminal_safe  # noqa
from sphinx.util.docutils import docutils_namespace, patch_docutils
from sphinx.util.docutils import sphinx_domains

from rst_lsp.docutils_ext.parser import parse_source
from rst_lsp.docutils_ext.reporter import new_document
from rst_lsp.docutils_ext.visitor import DocInfoVisitor


@attr.s
class SphinxAppEnv:
    app: Sphinx = attr.ib()
    roles: dict = attr.ib()
    directives: dict = attr.ib()
    stream_status: IO = attr.ib()
    stream_error: IO = attr.ib()


def create_sphinx_app(
    confdir=None, confoverrides=None, source_dir=None, output_dir=None
) -> Tuple[Sphinx, dict, dict]:
    """Yield a Sphinx Application, within a context.

    This context implements the standard sphinx patches to docutils,
    including the addition of builtin and extension roles and directives.

    Parameters
    ----------
    confdir : str or None
        path where configuration file (conf.py) is located
    confoverrides : dict or None
        dictionary containing parameters that will update those set from conf.py

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
            from docutils.parsers.rst.directives import _directives
            from docutils.parsers.rst.roles import _roles

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
            roles = copy.copy(_roles)
            directives = copy.copy(_directives)

    except (Exception, KeyboardInterrupt) as exc:
        # handle_exception(app, args, exc, error)
        raise exc
    finally:
        if not source_dir:
            shutil.rmtree(sourcedir, ignore_errors=True)
        if not output_dir:
            shutil.rmtree(outputdir, ignore_errors=True)

    return SphinxAppEnv(app, roles, directives, log_stream_status, log_stream_warning)


@contextmanager
def sphinx_env(app_env: SphinxAppEnv):
    with patch_docutils(app_env.app.confdir), docutils_namespace():
        from docutils.parsers.rst.directives import _directives
        from docutils.parsers.rst.roles import _roles

        if app_env.roles:
            _roles.update(app_env.roles)
        if app_env.directives:
            _directives.update(app_env.directives)

        with sphinx_domains(app_env.app.env):
            yield


def retrieve_namespace(app_env: SphinxAppEnv):
    """Retrieve all available roles and directives."""
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
    with sphinx_env(app_env):
        from docutils.parsers.rst.directives import _directives, _directive_registry
        from docutils.parsers.rst.roles import _roles, _role_registry

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
        for domain_name in app_env.app.env.domains:
            domain = app_env.app.env.get_domain(domain_name)
            prefix = "" if domain.name == "std" else f"{domain.name}:"
            # TODO 'default_domain' is also looked up by
            # sphinx.util.docutils.sphinx_domains.lookup_domain_element
            for role_name, role in domain.roles.items():
                all_roles[f"{prefix}{role_name}"] = role
            for direct_name, direct in domain.directives.items():
                all_roles[f"{prefix}{direct_name}"] = direct
    return all_roles, all_directives


@attr.s
class SourceAssessResult:
    doctree: document = attr.ib()
    elements: List[dict] = attr.ib()
    linting: List[dict] = attr.ib()


def assess_source(
    content: str, app_env: SphinxAppEnv, filename: str = "input.rst",
) -> SourceAssessResult:
    """Assess the content of an file.

    Parameters
    ----------
    content : str
        the content of the file
    filename : str
        the file path

    Returns
    -------
    SourceAssessResult

    """
    with sphinx_env(app_env):

        # TODO maybe sub-class sphinx.io.SphinxStandaloneReader?
        # (see also sphinx.testing.restructuredtext.parse, for a basic implementation)
        settings = OptionParser(components=(RSTParser,)).get_default_values()
        app_env.app.env.prepare_settings(filename)
        settings.env = app_env.app.env
        doc_warning_stream = StringIO()
        settings.warning_stream = doc_warning_stream
        settings.report_level = 2  # warning
        settings.halt_level = 4  # severe
        # The level at or above which `SystemMessage` exceptions
        # will be raised, halting execution.

        document, reporter = new_document(content, settings=settings)

        try:
            parse_source(content, document)
        except SystemMessage:
            pass

        visitor = DocInfoVisitor(document, content)
        document.walk(visitor)
        elements = visitor.info_datas[:]

    return SourceAssessResult(document, elements, reporter.log_capture,)

    # from docutils.parsers.rst import states
    # for state in states.state_classes:
    #     print(state)
