"""These are effectively a copy of the standard docutils element,
but only containing JSON friendly data, to store in the database.
"""
import attr


@attr.s(kw_only=True)
class BlockElement:
    lineno: int = attr.ib()
    start_char = attr.ib(None)


@attr.s(kw_only=True)
class SectionElement(BlockElement):
    level: int = attr.ib()
    length: int = attr.ib()
    # node


@attr.s(kw_only=True)
class DirectiveElement(BlockElement):
    arguments: str = attr.ib()
    options: int = attr.ib()
    klass: str = attr.ib()
    # indented


@attr.s(kw_only=True)
class InlineElement:
    parent: object = attr.ib(None)
    lineno: int = attr.ib()
    # NB: start_char count currently starts at the indentation level
    # and may continue to the next line, if no blank line
    start_char: int = attr.ib()
    raw: str = attr.ib()


@attr.s(kw_only=True)
class RoleElement(InlineElement):
    role: str = attr.ib()
    content: str = attr.ib()


@attr.s(kw_only=True)
class LinkElement(InlineElement):
    alias: str = attr.ib()
    link_type: str = attr.ib()
    alt_text: str = attr.ib()


@attr.s(kw_only=True)
class RefElement(InlineElement):
    alias: str = attr.ib()
    ref_type: str = attr.ib()
