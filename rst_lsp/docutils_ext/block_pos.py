from types import FunctionType, MethodType

from docutils import nodes
from docutils.parsers.rst import DirectiveError, Parser, states


def get_state_classes():
    # state classes are parsed to the StateMachine class
    # and convert to a dict, with keys denoted by the class names
    # therefore sub-classes, must be named the same as their parent.
    return (
        Body,
        states.BulletList,
        states.DefinitionList,
        states.EnumeratedList,
        states.FieldList,
        states.OptionList,
        states.LineBlock,
        states.ExtensionOptions,
        Explicit,
        Text,
        states.Definition,
        Line,
        SubstitutionDef,
    )


class RSTParserCustom(Parser):
    def __init__(self, inliner=None):
        self.initial_state = "Body"
        self.state_classes = get_state_classes()
        for state_class in self.state_classes:
            # flush any cached states from the last parse
            state_class.nested_sm_cache = []
        self.inliner = inliner


class PosSection(nodes.Element, nodes.Invisible):
    """A node which stores the source text position in the document, of its children."""

    def __init__(self, *, start_line, level, title, section):
        """Initialisation

        Parameters
        ----------
        start: list
            [<start line>, <start column>]
        level: int
        title: str
        section: nodes.section
        """
        attributes = {"start_line": start_line, "level": level}
        children = [section]
        super().__init__(title, *children, **attributes)

    @property
    def line_start(self):
        return self.attributes["start_line"]

    @property
    def line_end(self):
        return self.attributes.get("end_line", None)

    @property
    def level(self):
        return self.attributes["level"]


class PosExplicit(nodes.Element, nodes.Invisible):
    """A node which stores the source text position in the document, of its children."""

    def __init__(self, *, etype, start_line, end_line, children):
        """Initialisation

        etype can be one of:
        'footnote', 'citation', 'hyperlink_target', 'substitution_def'
        """
        attributes = {"type": etype, "start_line": start_line, "end_line": end_line}
        super().__init__("", *children, **attributes)

    @property
    def line_start(self):
        return self.attributes["start_line"]

    @property
    def line_end(self):
        return self.attributes.get("end_line", None)

    @property
    def etype(self):
        return self.attributes.get("type", None)


class PosDirective(nodes.Element, nodes.Invisible):
    """A node which stores the source text position in the document, of its children."""

    def __init__(self, *, rawsource, line_start, line_end, children, **attributes):
        """Initialisation
        """
        attributes.update({"line_start": line_start, "line_end": line_end})
        super().__init__(rawsource, *children, **attributes)

    @property
    def line_start(self):
        return self.attributes["line_start"]

    @property
    def line_end(self):
        return self.attributes["line_end"]

    @property
    def line_content(self):
        return self.attributes["line_content"]

    @property
    def content_indent(self):
        return self.attributes["content_indent"]

    @property
    def dname(self):
        return self.attributes["dtype"]

    @property
    def arguments(self):
        return self.attributes["arguments"]

    @property
    def options(self):
        return self.attributes["options"]

    @property
    def klass(self):
        return self.attributes["klass"]


class SectionMixin:
    def new_subsection(self, title, lineno, messages):
        """Append new subsection to document tree. On return, check level."""
        memo = self.memo
        mylevel = memo.section_level
        memo.section_level += 1
        section_node = nodes.section()
        position = PosSection(
            start_line=lineno - 1,
            level=memo.section_level,
            title=title,
            section=section_node,
        )
        self.parent += position
        textnodes, title_messages = self.inline_text(title, lineno)
        titlenode = nodes.title(title, "", *textnodes)
        name = nodes.fully_normalize_name(titlenode.astext())
        section_node["names"].append(name)
        section_node += titlenode
        section_node += messages
        section_node += title_messages
        self.document.note_implicit_target(section_node, section_node)
        offset = self.state_machine.line_offset + 1
        absoffset = self.state_machine.abs_line_offset() + 1
        newabsoffset = self.nested_parse(
            self.state_machine.input_lines[offset:],
            input_offset=absoffset,
            node=section_node,
            match_titles=True,
        )
        # TODO this line can be one greater than the number of actual lines
        position["end_line"] = newabsoffset - 1
        self.goto_line(newabsoffset)
        if memo.section_level <= mylevel:  # can't handle next section?
            raise EOFError  # bubble up to supersection
        # reset section_level; next pass will detect it properly
        memo.section_level = mylevel


class ExplicitMixin:
    def explicit_construct(self, match):
        """Determine which explicit construct this is, parse & return it."""
        errors = []
        for method, pattern in self.explicit.constructs:
            expmatch = pattern.match(match.string)
            if expmatch:
                lineno = self.state_machine.abs_line_number()
                try:
                    nodelist, finish = method(self, expmatch)
                except states.MarkupError as error:
                    lineno = self.state_machine.abs_line_number()
                    message = " ".join(error.args)
                    errors.append(self.reporter.warning(message, line=lineno))
                    break
                else:
                    if method.__name__ in [
                        "footnote",
                        "citation",
                        "hyperlink_target",
                        "substitution_def",
                    ]:
                        return (
                            PosExplicit(
                                etype=method.__name__,
                                start_line=lineno - 1,
                                end_line=self.state_machine.abs_line_number() - 1,
                                children=nodelist,
                            ),
                            finish,
                        )
                    return nodelist, finish
        nodelist, blank_finish = self.comment(match)
        return nodelist + errors, blank_finish

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
        except nodes.MarkupError as detail:
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

        # NOTE it would be ideal to also record the start and end characters on lines?
        # However, it appears that nested state machine are initalised with
        # pre de-dented input lines, and do not record the initial indentation
        position = PosDirective(
            rawsource=block_text,
            line_start=line_offset,
            line_end=self.state_machine.abs_line_number() - 1,
            # the line at which content starts
            line_content=content_offset if content else None,
            content_indent=indent
            if content
            else None,  # relative to initial indent of directive
            dtype=type_name,
            arguments=arguments,
            options=options,
            klass=f"{directive.__module__}.{directive.__name__}",
            children=result,
        )
        return (
            position,
            blank_finish or self.state_machine.is_next_line_blank(),
        )


class Body(SectionMixin, ExplicitMixin, states.Body):
    def __init__(self, state_machine, debug=False):
        super().__init__(state_machine, debug=debug)
        self.nested_sm_kwargs = {
            "state_classes": get_state_classes(),
            "initial_state": "Body",
        }


class Explicit(ExplicitMixin, states.Explicit):
    pass


class SubstitutionDef(states.SubstitutionDef):
    # TODO substitutions can embed directives
    # note, in this case, that the PosDirective should be inside the PosExplicit
    pass


class Line(SectionMixin, states.Line):
    def __init__(self, state_machine, debug=False):
        super().__init__(state_machine, debug=debug)
        self.nested_sm_kwargs = {
            "state_classes": get_state_classes(),
            "initial_state": "Body",
        }


class Text(SectionMixin, states.Text):
    def __init__(self, state_machine, debug=False):
        super().__init__(state_machine, debug=debug)
        self.nested_sm_kwargs = {
            "state_classes": get_state_classes(),
            "initial_state": "Body",
        }
