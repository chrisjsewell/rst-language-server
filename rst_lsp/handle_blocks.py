from docutils import nodes
from docutils.parsers.rst.states import MarkupError

from .elements import SectionElement, DirectiveElement

_BLOCK_OBJECTS = []


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
