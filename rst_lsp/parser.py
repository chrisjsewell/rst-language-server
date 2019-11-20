from contextlib import contextmanager
from collections import namedtuple
import copy

from io import StringIO
import locale
import os
import shutil
import tempfile
from unittest import mock

from docutils import nodes
from docutils.frontend import OptionParser

# from docutils.parsers import get_parser_class
from docutils.parsers.rst import Parser as RSTParser
from docutils.parsers.rst.directives import _directives
from docutils.parsers.rst.roles import _roles
from docutils.parsers.rst.states import Body, Inliner, MarkupError, RSTState

# from docutils.utils import new_document
from docutils.utils import decode_path, Reporter  # , SystemMessage, unescape

from sphinx import package_dir
import sphinx.locale
from sphinx.application import Sphinx
from sphinx.util.console import nocolor, color_terminal, terminal_safe  # noqa
from sphinx.util.docutils import docutils_namespace, patch_docutils

# import yaml


sphinx_init = namedtuple(
    "sphinx_init", ["app", "directives", "roles", "log_status", "log_warnings"]
)


@contextmanager
def init_sphinx(
    confdir=None, confoverrides=None, source_dir=None, output_dir=None
) -> sphinx_init:
    """Initialise the Sphinx Application"""

    # below is taken from sphinx.cmd.build.main
    sphinx.locale.setlocale(locale.LC_ALL, "")
    sphinx.locale.init_console(os.path.join(package_dir, "locale"), "sphinx")

    # below is adapted from sphinx.cmd.build.build_main
    confdir = None
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
            yield sphinx_init(
                app,
                _directives,
                _roles,
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


directive_info = namedtuple(
    "directive_info", ["indented", "lineno", "cls", "options", "arguments"]
)
role_info = namedtuple("role_info", ["raw", "text", "name", "lineno", "cls"])
section_info = namedtuple("section_info", ["length", "lineno", "node", "level"])

_element_info = {}


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
    _element_info.setdefault("directives", []).append(
        directive_info(type(indented), line_offset, directive, options, arguments)
    )
    # end patch
    if content and not has_content:
        raise MarkupError("no content permitted")
    return (arguments, options, content, content_offset)


def interpreted(self, rawsource, text, role, lineno):
    from docutils.parsers.rst import roles

    role_fn, messages = roles.role(role, self.language, lineno, self.reporter)
    # patch
    _element_info.setdefault("roles", []).append(
        role_info(rawsource, text, role, lineno, role_fn)
    )
    # end patch
    if role_fn:
        nodes, messages2 = role_fn(role, rawsource, text, lineno, self)
        return nodes, messages + messages2
    else:
        msg = self.reporter.error(
            'Unknown interpreted text role "%s".' % role, line=lineno
        )
        return ([self.problematic(rawsource, rawsource, msg)], messages + [msg])


# def interpreted_or_phrase_ref(self, match, lineno):
#     end_pattern = self.patterns.interpreted_or_phrase_ref
#     string = match.string
#     matchstart = match.start('backquote')
#     matchend = match.end('backquote')
#     rolestart = match.start('role')
#     role = match.group('role')
#     position = ''
#     if role:
#         role = role[1:-1]
#         position = 'prefix'
#     elif self.quoted_start(match):
#         return (string[:matchend], [], string[matchend:], [])
#     endmatch = end_pattern.search(string[matchend:])
#     if endmatch and endmatch.start(1):  # 1 or more chars
#         textend = matchend + endmatch.end()
#         if endmatch.group('role'):
#             if role:
#                 msg = self.reporter.warning(
#                     'Multiple roles in interpreted text (both '
#                     'prefix and suffix present; only one allowed).',
#                     line=lineno)
#                 text = unescape(string[rolestart:textend], True)
#                 prb = self.problematic(text, text, msg)
#                 return string[:rolestart], [prb], string[textend:], [msg]
#             role = endmatch.group('suffix')[1:-1]
#             position = 'suffix'
#         escaped = endmatch.string[:endmatch.start(1)]
#         rawsource = unescape(string[matchstart:textend], True)
#         if rawsource[-1:] == '_':
#             if role:
#                 msg = self.reporter.warning(
#                         'Mismatch: both interpreted text role %s and '
#                         'reference suffix.' % position, line=lineno)
#                 text = unescape(string[rolestart:textend], True)
#                 prb = self.problematic(text, text, msg)
#                 return string[:rolestart], [prb], string[textend:], [msg]
#             return self.phrase_ref(string[:matchstart], string[textend:],
#                                     rawsource, escaped, unescape(escaped))
#         else:
#             rawsource = unescape(string[rolestart:textend], True)
#             # patch starts
#             from docutils.parsers.rst import roles
#             role_fn, messages = roles.role(role, self.language, lineno,
#                                             self.reporter)
#             _element_info["roles"].append(
#                 role_info(rawsource, escaped, role, lineno,
#                           role_fn, rolestart, textend, match.pos))
#             # patch ends
#             nodelist, messages = self.interpreted(rawsource, escaped, role,
#                                                     lineno)
#             return (string[:rolestart], nodelist,
#                     string[textend:], messages)
#     msg = self.reporter.warning(
#             'Inline interpreted text or phrase reference start-string '
#             'without end-string.', line=lineno)
#     text = unescape(string[matchstart:matchend], True)
#     prb = self.problematic(text, text, msg)
#     return string[:matchstart], [prb], string[matchend:], [msg]


# def literal(self, match, lineno):
#     """This would turn literals, e.g. ``a=1`` into math, e.g. $a=1$ """
#     before, inlines, remaining, sysmessages, endstring = self.inline_obj(
#         match, lineno, self.patterns.literal, nodes.math,
#         restore_backslashes=True)
#     return before, inlines, remaining, sysmessages


# dispatch = {'*': Inliner.emphasis,
#             '**': Inliner.strong,
#             '`': interpreted_or_phrase_ref,
#             '``': Inliner.literal,
#             '_`': Inliner.inline_internal_target,
#             ']_': Inliner.footnote_reference,
#             '|': Inliner.substitution_reference,
#             '_': Inliner.reference,
#             '__': Inliner.anonymous_reference}


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
        _element_info.setdefault("sections", []).append(
            section_info(len(block), input_offset, node, self.memo.section_level)
        )
    # _element_info.setdefault("blocks", []).append(
    #     block_info(len(block), input_offset, node))
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


# @mock.patch.object(Inliner, 'dispatch', dispatch)
# @mock.patch.object(Inliner, 'interpreted_or_phrase_ref', interpreted_or_phrase_ref)
# @mock.patch.object(Inliner, 'literal', literal)
@mock.patch.object(Inliner, "interpreted", interpreted)
@mock.patch.object(Body, "parse_directive_block", parse_directive_block)
@mock.patch.object(RSTState, "nested_parse", nested_parse)
def run_parser(source, doc):
    global _element_info
    _element_info = {}
    parser = RSTParser()
    parser.parse(source, doc)
    return {k: copy.copy(v) for k, v in _element_info.items()}


class CustomReporter(Reporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_capture = []

    def system_message(self, level, message, *children, **kwargs):
        sys_message = super().system_message(level, message, *children, **kwargs)
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
    ["environment", "roles", "directives", "element_info", "line_lookup", "errors"],
)


def assess_source(content, filename="input.rst", confdir=None, confoverrides=None):

    with init_sphinx(confdir=confdir, confoverrides=confoverrides) as sphinx_init:

        settings = OptionParser(components=(RSTParser,)).get_default_values()
        sphinx_init.app.env.prepare_settings(filename)
        settings.env = sphinx_init.app.env
        doc_warning_stream = StringIO()
        settings.warning_stream = doc_warning_stream

        document, reporter = new_document_custom(content, settings=settings)

        element_info = run_parser(content, document)

        line_lookup = {}
        for key, el_list in element_info.items():
            for el in el_list:
                line_lookup.setdefault(el.lineno, []).append(el)

    return SourceAssessResult(
        sphinx_init.app.env,
        sphinx_init.roles,
        sphinx_init.directives,
        element_info,
        line_lookup,
        reporter.log_capture,
    )

    # print(document.pformat())
    # print(document.children)
    # from docutils.parsers.rst import states
    # for state in states.state_classes:
    #     print(state)
