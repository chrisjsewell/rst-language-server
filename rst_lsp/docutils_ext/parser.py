"""This module provides a patch for classes in ``docutils.parsers.rst.states``.

``parse_source`` provides a parsing function with patches applied,
to inject ``InfoNodeBlock`` docutils elements into the parsed doctree.
This allows for line numbers and character columns to be obtained for certain elements,
during a subsequent ``document.walk``.

TODO it would be desirable to subclass these classes,
and inject them into the parsing process.
However, it is not readily apparent how this is achievable,
since docutils appears to hard-wire in a number of class dependencies.

"""
from unittest import mock
from types import FunctionType, MethodType

from docutils import nodes

# from docutils.parsers import get_parser_class
from docutils.parsers.rst import Parser as RSTParser
from docutils.parsers.rst.states import MarkupError, Body, RSTState
from docutils.parsers.rst import DirectiveError

from rst_lsp.docutils_ext.inliner import LSPInliner

__all__ = ("InfoNodeBlock", "parse_source")


class InfoNodeBlock(nodes.Node):
    """A node for highlighting a position in the document."""

    def __init__(self, dtype, doc_lineno, match=None, data={}):
        self.match = match
        self.dtype = dtype
        self.doc_lineno = doc_lineno
        self.other_data = data or {}
        self.children = []

    def astext(self):
        return f'<InfoNodeBlock "{self.dtype}" doc_line={self.doc_lineno}>'

    def pformat(self, indent="    ", level=0):
        """Return an indented pseudo-XML representation, for test purposes."""
        return indent * level + self.astext() + "\n"

    def __repr__(self):
        return self.astext()

    def shortrepr(self):
        return self.astext()


# from docutils.parsers.rst.states.Block
def run_directive(self, directive, match, type_name, option_presets):
    """
    Parse a directive then run its directive function.

    Parameters:

    - `directive`: The class implementing the directive.  Must be
        a subclass of `rst.Directive`.

    - `match`: A regular expression match object which matched the first
        line of the directive.

    - `type_name`: The directive name, as used in the source text.

    - `option_presets`: A dictionary of preset options, defaults for the
        directive options.  Currently, only an "alt" option is passed by
        substitution definitions (value: the substitution name), which may
        be used by an embedded image directive.

    Returns a 2-tuple: list of nodes, and a "blank finish" boolean.
    """
    if isinstance(directive, (FunctionType, MethodType)):
        from docutils.parsers.rst import convert_directive_function

        directive = convert_directive_function(directive)
    lineno = self.state_machine.abs_line_number()
    initial_line_offset = self.state_machine.line_offset
    (
        indented,
        indent,
        line_offset,
        blank_finish,
    ) = self.state_machine.get_first_known_indented(match.end(), strip_top=0)
    block_text = "\n".join(
        self.state_machine.input_lines[
            initial_line_offset : self.state_machine.line_offset + 1
        ]
    )
    try:
        arguments, options, content, content_offset = self.parse_directive_block(
            indented, line_offset, directive, option_presets
        )
    except MarkupError as detail:
        error = self.reporter.error(
            'Error in "%s" directive:\n%s.' % (type_name, " ".join(detail.args)),
            nodes.literal_block(block_text, block_text),
            line=lineno,
        )
        return [error], blank_finish
    directive_instance = directive(
        type_name,
        arguments,
        options,
        content,
        lineno,
        content_offset,
        block_text,
        self,
        self.state_machine,
    )
    try:
        result = directive_instance.run()
    except DirectiveError as error:
        msg_node = self.reporter.system_message(error.level, error.msg, line=lineno)
        msg_node += nodes.literal_block(block_text, block_text)
        result = [msg_node]
    assert isinstance(result, list), (
        'Directive "%s" must return a list of nodes.' % type_name
    )
    for i in range(len(result)):
        assert isinstance(result[i], nodes.Node), (
            'Directive "%s" returned non-Node object (index %s): %r'
            % (type_name, i, result[i])
        )
    info = InfoNodeBlock(
        dtype="directive",
        doc_lineno=line_offset + 1,
        match=match,
        data=dict(
            type_name=type_name,
            arguments=arguments,
            options=options,
            klass=f"{directive.__module__}.{directive.__name__}",
        ),
    )
    return ([info] + result, blank_finish or self.state_machine.is_next_line_blank())


# from docutils.parsers.rst.states.RSTState
def section(self, title, source, style, lineno, messages):
    """Check for a valid subsection and create one if it checks out."""
    if self.check_subsection(source, style, lineno):
        info = InfoNodeBlock(
            dtype="section",
            doc_lineno=lineno,
            data={"level": self.memo.section_level + 1, "title": title},
        )
        self.parent += info
        self.new_subsection(title, lineno, messages)
        info.other_data["endline"] = self.state_machine.abs_line_offset()


# from docutils.parsers.rst.states.Block
def explicit_construct(self, match):
    """Determine which explicit construct this is, parse & return it."""
    errors = []
    for method, pattern in self.explicit.constructs:
        expmatch = pattern.match(match.string)
        if expmatch:
            lineno = self.state_machine.abs_line_number()
            try:
                nodelist, finish = method(self, expmatch)
            except MarkupError as error:
                message = " ".join(error.args)
                errors.append(self.reporter.warning(message, line=lineno))
                break
            else:
                ctype = None
                info = []
                for meth, name in [
                    (Body.footnote, "footnote"),
                    (Body.citation, "citation"),
                    (Body.hyperlink_target, "hyperlink_target"),
                    (Body.substitution_def, "substitution_def"),
                ]:
                    if meth == method:
                        ctype = name
                        break
                if ctype:
                    info = [
                        InfoNodeBlock(
                            dtype="explicit_construct",
                            doc_lineno=lineno,
                            data={"ctype": ctype, "raw": match.string},
                        )
                    ]
                return info + nodelist, finish
    nodelist, blank_finish = self.comment(match)
    return nodelist + errors, blank_finish

    # explicit.constructs = [
    #       (footnote,
    #        re.compile(r"""
    #                   \.\.[ ]+          # explicit markup start
    #                   \[
    #                   (                 # footnote label:
    #                       [0-9]+          # manually numbered footnote
    #                     |               # *OR*
    #                       \#              # anonymous auto-numbered footnote
    #                     |               # *OR*
    #                       \#%s            # auto-number ed?) footnote label
    #                     |               # *OR*
    #                       \*              # auto-symbol footnote
    #                   )
    #                   \]
    #                   ([ ]+|$)          # whitespace or end of line
    #                   """ % Inliner.simplename, re.VERBOSE | re.UNICODE)),
    #       (citation,
    #        re.compile(r"""
    #                   \.\.[ ]+          # explicit markup start
    #                   \[(%s)\]          # citation label
    #                   ([ ]+|$)          # whitespace or end of line
    #                   """ % Inliner.simplename, re.VERBOSE | re.UNICODE)),
    #       (hyperlink_target,
    #        re.compile(r"""
    #                   \.\.[ ]+          # explicit markup start
    #                   _                 # target indicator
    #                   (?![ ]|$)         # first char. not space or EOL
    #                   """, re.VERBOSE | re.UNICODE)),
    #       (substitution_def,
    #        re.compile(r"""
    #                   \.\.[ ]+          # explicit markup start
    #                   \|                # substitution indicator
    #                   (?![ ]|$)         # first char. not space or EOL
    #                   """, re.VERBOSE | re.UNICODE)),
    #       (directive,
    #        re.compile(r"""
    #                   \.\.[ ]+          # explicit markup start
    #                   (%s)              # directive name
    #                   [ ]?              # optional space
    #                   ::                # directive delimiter
    #                   ([ ]+|$)          # whitespace or end of line
    #                   """ % Inliner.simplename, re.VERBOSE | re.UNICODE))]


@mock.patch.object(Body, "explicit_construct", explicit_construct)
@mock.patch.object(Body, "run_directive", run_directive)
@mock.patch.object(RSTState, "section", section)
def parse_source(
    source: str,
    document: nodes.document,
    parser_cls: RSTParser = None,
    inliner_cls: LSPInliner = None,
) -> None:
    """Parse source text to populate a document

    The parsing runs with patches applied to the standard docutils state classes,
    to inject ``InfoNodeBlock`` docutils elements into the populated doctree.

    """
    # TODO see also sphinx/testing/restructuredtext.py
    # NOTE https://www.sphinx-doc.org/en/master/extdev/index.html#build-phases
    if inliner_cls is None:
        inliner_cls = LSPInliner
    if parser_cls is None:
        parser_cls = RSTParser
    inliner = inliner_cls(doc_text=source)
    parser = parser_cls(inliner=inliner)  # type: RSTParser
    parser.parse(source, document)
