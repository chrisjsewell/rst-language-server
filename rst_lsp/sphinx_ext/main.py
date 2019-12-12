"""Module for building a mapping of document/line/character to RST elements.

This modules contains `sphinx_env`,
which is a context manager, that allows sphinx to be initialised,
outside of the command-line.

"""
from contextlib import contextmanager
import copy
from io import StringIO
from importlib import import_module
import locale
import os
import shutil
import tempfile
import threading
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

from rst_lsp.docutils_ext.block_lsp import RSTParserCustom
from rst_lsp.docutils_ext.inliner_lsp import InlinerLSP
from rst_lsp.docutils_ext.reporter import new_document
from rst_lsp.docutils_ext.visitor_lsp import LSPTransform
from rst_lsp.server.datatypes import DocumentSymbol


@attr.s
class SphinxAppEnv:
    app: Sphinx = attr.ib()
    roles: dict = attr.ib()
    directives: dict = attr.ib()
    additional_nodes: set = attr.ib()
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
            from sphinx.util.docutils import additional_nodes

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
            additional_nodes = copy.copy(additional_nodes)

    except (Exception, KeyboardInterrupt) as exc:
        # handle_exception(app, args, exc, error)
        raise exc
    finally:
        if not source_dir:
            shutil.rmtree(sourcedir, ignore_errors=True)
        if not output_dir:
            shutil.rmtree(outputdir, ignore_errors=True)

    return SphinxAppEnv(
        app, roles, directives, additional_nodes, log_stream_status, log_stream_warning
    )


@contextmanager
def sphinx_env(app_env: SphinxAppEnv):
    with patch_docutils(app_env.app.confdir), docutils_namespace():
        from docutils.parsers.rst.directives import _directives
        from docutils.parsers.rst.roles import _roles
        from sphinx.util.docutils import register_node

        if app_env.roles:
            _roles.update(app_env.roles)
        if app_env.directives:
            _directives.update(app_env.directives)
        for node in app_env.additional_nodes:
            register_node(node)

        with sphinx_domains(app_env.app.env):
            yield


def retrieve_namespace(app_env: SphinxAppEnv):
    """Retrieve all available roles, directives and additional nodes."""
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

    # we use a threading lock to guard against the globals _directives and _roles
    # being changed before they can be read.
    with threading.Lock():
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


def find_all_files(srcdir: str, exclude_patterns: List[str], suffixes=(".rst",)):
    """Adapted from ``sphinx.environment.BuildEnvironment.find_files``"""
    from sphinx.project import EXCLUDE_PATHS
    from sphinx.util import get_matching_files
    from sphinx.util.matching import compile_matchers

    exclude_patterns.extend(EXCLUDE_PATHS)
    excludes = compile_matchers(exclude_patterns)
    docnames = set()
    for filename in get_matching_files(srcdir, excludes):
        if not any(filename.endswith(s) for s in suffixes):
            continue
        if os.access(os.path.join(srcdir, filename), os.R_OK):
            filename = os.path.realpath(filename)
            docnames.add(filename)
            # modified_time = os.path.getmtime(filename)
            # TODO add/update os.path.getmtime for files in DB when saved/closed
            # Then we can test against the DB to check which files need to be re-read
            # also remove files from db that are no longer required
            # re-read all files in background (async tinydb?)
            # send progress to client (will require next LSP version 3.15.0)
    return docnames


@attr.s(kw_only=True)
class SourceAssessResult:
    doctree: document = attr.ib()
    positions: List[dict] = attr.ib()
    references: List[dict] = attr.ib()
    name_to_target: List[dict] = attr.ib()
    doc_symbols: List[DocumentSymbol] = attr.ib()
    linting: List[dict] = attr.ib()


def assess_source(
    content: str, app_env: SphinxAppEnv, doc_uri: str = "input.rst",
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
    # TODO how can we guard against globals like _directives and _roles
    # being changed by another thread, without thread locking the entire function?
    with sphinx_env(app_env):

        # TODO look at sphinx.io.read_doc function, that is used for sphinx parsing
        # (see also sphinx.testing.restructuredtext.parse, for a basic implementation)
        settings = OptionParser(components=(RSTParser,)).get_default_values()
        app_env.app.env.prepare_settings(doc_uri)
        settings.env = app_env.app.env
        doc_warning_stream = StringIO()
        settings.warning_stream = doc_warning_stream
        settings.report_level = 2  # warning
        settings.halt_level = 4  # severe
        # The level at or above which `SystemMessage` exceptions
        # will be raised, halting execution.

        document, reporter = new_document(doc_uri, settings=settings)

        parser = RSTParserCustom(inliner=InlinerLSP(doc_text=content))
        try:
            parser.parse(content, document)
        except SystemMessage:
            pass

        transform = LSPTransform(document)
        transform.apply(content)

    return SourceAssessResult(
        doctree=document,
        positions=transform.db_positions,
        references=transform.db_references,
        name_to_target=transform.name_to_uuid,
        doc_symbols=transform.db_doc_symbols,
        linting=reporter.log_capture,
    )
