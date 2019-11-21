"""Module for building a mapping of document/line/character to RST elements. 

This modules contains `init_sphinx`,
which is a context manager, that allows sphinx to be initialised,
outside of the command-line, and also collects all available roles and directives.

``run_parser`` then patches a number of the docutils classes,
to allow for line numbers and character columns to be obtained for certain elements.

Note, it would be desirable to subclass these classes.
However, docutils does not make these easy,
because it hard-wires in a number of class dependencies.
For example a lot of the state functions return 'Body', as mapping to the Body class

"""
from contextlib import contextmanager
from collections import namedtuple
import copy
from io import StringIO
from importlib import import_module
import locale
import os
import shutil
import tempfile
from unittest import mock

from docutils import nodes
from docutils.frontend import OptionParser

# from docutils.parsers import get_parser_class
from docutils.parsers.rst import Parser as RSTParser

# from docutils.parsers.rst.directives import _directives
# from docutils.parsers.rst.roles import _roles
# from docutils.parsers.rst import states
from docutils.parsers.rst.states import Body, MarkupError, RSTState

# from docutils.utils import new_document
from docutils.utils import (
    decode_path,
    Reporter,
)  # , escape2null, SystemMessage, unescape

from sphinx import package_dir
import sphinx.locale
from sphinx.application import Sphinx
from sphinx.util.console import nocolor, color_terminal, terminal_safe  # noqa
from sphinx.util.docutils import docutils_namespace, patch_docutils
from sphinx.util.docutils import sphinx_domains

from .inliner import CustomInliner
from .elements import SectionElement, DirectiveElement

_BLOCK_OBJECTS = []


sphinx_init = namedtuple(
    "sphinx_init", ["app", "directives", "roles", "log_status", "log_warnings"]
)


@contextmanager
def init_sphinx(
    confdir=None, confoverrides=None, source_dir=None, output_dir=None
) -> sphinx_init:
    """Initialise the Sphinx Application"""

    # below is taken from sphinx.cmd.build.main
    # note: this may be removed in future
    sphinx.locale.setlocale(locale.LC_ALL, "")
    sphinx.locale.init_console(os.path.join(package_dir, "locale"), "sphinx")

    # below is adapted from sphinx.cmd.build.build_main
    confdir = confdir
    confoverrides = confoverrides or {}

    builder = "html"
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
                    app,
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


def parse_directive_block(self, indented, line_offset, directive, option_presets):

    option_spec = directive.option_spec
    has_content = directive.has_content
    if indented and not indented[0].strip():
        indented.trim_start()
        line_offset += 1
    while indented and not indented[-1].strip():
        indented.trim_end()
    if indented and (
        directive.required_arguments or directive.optional_arguments or option_spec
    ):
        for i, line in enumerate(indented):
            if not line.strip():
                break
        else:
            i += 1
        arg_block = indented[:i]
        content = indented[i + 1 :]
        content_offset = line_offset + i + 1
    else:
        content = indented
        content_offset = line_offset
        arg_block = []
    if option_spec:
        options, arg_block = self.parse_directive_options(
            option_presets, option_spec, arg_block
        )
    else:
        options = {}
    if arg_block and not (directive.required_arguments or directive.optional_arguments):
        content = arg_block + indented[i:]
        content_offset = line_offset
        arg_block = []

    while content and not content[0].strip():
        content.trim_start()
        content_offset += 1
    if directive.required_arguments or directive.optional_arguments:
        arguments = self.parse_directive_arguments(directive, arg_block)
    else:
        arguments = []
    # patch
    _BLOCK_OBJECTS.append(
        DirectiveElement(
            lineno=line_offset,
            arguments=arguments,
            options=options,
            klass=f"{directive.__module__}.{directive.__name__}",
        )
    )
    # end patch
    if content and not has_content:
        raise MarkupError("no content permitted")
    return (arguments, options, content, content_offset)


def nested_parse(
    self,
    block,
    input_offset,
    node,
    match_titles=False,
    state_machine_class=None,
    state_machine_kwargs=None,
):
    """
    Create a new StateMachine rooted at `node` and run it over the input
    `block`.
    """
    # patch
    if isinstance(node, nodes.section):
        _BLOCK_OBJECTS.append(
            SectionElement(
                lineno=input_offset, level=self.memo.section_level, length=len(block)
            )
        )
    # end patch
    use_default = 0
    if state_machine_class is None:
        state_machine_class = self.nested_sm
        use_default += 1
    if state_machine_kwargs is None:
        state_machine_kwargs = self.nested_sm_kwargs
        use_default += 1
    block_length = len(block)

    state_machine = None
    if use_default == 2:
        try:
            state_machine = self.nested_sm_cache.pop()
        except IndexError:
            pass
    if not state_machine:
        state_machine = state_machine_class(debug=self.debug, **state_machine_kwargs)
    state_machine.run(
        block, input_offset, memo=self.memo, node=node, match_titles=match_titles
    )
    if use_default == 2:
        self.nested_sm_cache.append(state_machine)
    else:
        state_machine.unlink()
    new_offset = state_machine.abs_line_offset()
    # No `block.parent` implies disconnected -- lines aren't in sync:
    if block.parent and (len(block) - block_length) != 0:
        # Adjustment for block if modified in nested parse:
        self.state_machine.next_line(len(block) - block_length)
    return new_offset


# TODO see also sphinx/testing/restructuredtext.py
# small function to parse a string as reStructuredText with premade Sphinx application
# @mock.patch.object(states, "Inliner", CustomInliner)
@mock.patch.object(Body, "parse_directive_block", parse_directive_block)
@mock.patch.object(RSTState, "nested_parse", nested_parse)
def run_parser(source, doc):
    """Parse the document, and return the gathered document elements."""
    # TODO https://www.sphinx-doc.org/en/master/extdev/index.html#build-phases
    global _BLOCK_OBJECTS
    _BLOCK_OBJECTS = []
    # CustomInliner.reset_inline_objects()
    inliner = CustomInliner(doc_text=source)
    parser = RSTParser(inliner=inliner)
    parser.parse(source, doc)
    return (
        _BLOCK_OBJECTS[:],
        # CustomInliner.inline_objects[:],
        inliner.inline_objects[:]
    )


class CustomReporter(Reporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_capture = []

    def system_message(self, level, message, *children, **kwargs):
        sys_message = super().system_message(level, message, *children, **kwargs)
        if level >= self.report_level:
            self.log_capture.append(
                {
                    # "source": sys_message["source"],
                    "line": sys_message.get("line", ""),
                    "type": sys_message["type"],
                    "level": sys_message["level"],
                    "description": nodes.Element.astext(sys_message),
                }
            )
        return sys_message


def new_document_custom(source_path, settings=None):
    """Return a new empty document object.

    Replicates ``docutils.utils.new_document``, but with a custom reporter.

    Parameters
    ----------
    source_path : str
        The path to or description of the source text of the document.
    settings : optparse.Values
        Runtime settings.  If none are provided, a default core set will
        be used.  If you will use the document object with any Docutils
        components, you must provide their default settings as well.  For
        example, if parsing, at least provide the parser settings,
        obtainable as follows::

            settings = docutils.frontend.OptionParser(
                components=(docutils.parsers.rst.Parser,)
                ).get_default_values()
    """
    # TODO cache creation, as in sphinx.util.docutils.new_document
    if settings is None:
        settings = OptionParser().get_default_values()
    source_path = decode_path(source_path)
    reporter = CustomReporter(
        source_path,
        settings.report_level,
        settings.halt_level,
        stream=settings.warning_stream,
        debug=settings.debug,
        encoding=settings.error_encoding,
        error_handler=settings.error_encoding_error_handler,
    )
    document = nodes.document(settings, reporter, source=source_path)
    document.note_source(source_path, -1)
    return document, reporter


SourceAssessResult = namedtuple(
    "SourceAssessResult",
    [
        "doctree",
        "environment",
        "roles",
        "directives",
        "block_objects",
        "inline_objects",
        "errors",
    ],
)


def assess_source(content, filename="input.rst", confdir=None, confoverrides=None):

    with init_sphinx(confdir=confdir, confoverrides=confoverrides) as sphinx_init:

        # TODO maybe sub-class sphinx.io.SphinxStandaloneReader?
        # (see also sphinx.testing.restructuredtext.parse, for a basic implementation)

        settings = OptionParser(components=(RSTParser,)).get_default_values()
        sphinx_init.app.env.prepare_settings(filename)
        settings.env = sphinx_init.app.env
        doc_warning_stream = StringIO()
        settings.warning_stream = doc_warning_stream
        settings.report_level = 2  # warning

        document, reporter = new_document_custom(content, settings=settings)

        block_objs, inline_objs = run_parser(content, document)

        # The parser does not account for indentation, when assigning `start_char`
        # (for inline_objs, this is handled by the custom Inliner)
        content_lines = content.splitlines()
        for block in block_objs:
            line = content_lines[block.lineno - 1]
            block.start_char = len(line) - len(line.lstrip())

        # from pprint import pprint
        # pprint(block_objs)
        # pprint(inline_objs)

    return SourceAssessResult(
        document,
        sphinx_init.app.env,
        sphinx_init.roles,
        sphinx_init.directives,
        block_objs,
        inline_objs,
        reporter.log_capture,
    )

    # from docutils.parsers.rst import states
    # for state in states.state_classes:
    #     print(state)
