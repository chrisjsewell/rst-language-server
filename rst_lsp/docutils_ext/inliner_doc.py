from functools import lru_cache
import re
from typing import Any, List, Tuple

from docutils import nodes
from docutils.utils import escape2null

from rst_lsp.docutils_ext.inliner_base import Inliner


class PosInline(nodes.Element, nodes.Inline, nodes.Invisible):
    """A node which stores the source text position in the document, of its children."""

    def __init__(self, *, stype, position, rawsource, children, **attributes):
        """Initialisation

        Parameters
        ----------
        stype : str
            The syntax type of the source text
        position : list
            [<start line>, <start column>, <end line>, <end column>]
        rawsource : str
        children : list
            inline nodes, created from the rawsource
        """
        attributes.update({"position": position, "type": stype})
        super().__init__(rawsource, *children, **attributes)


@lru_cache()
def get_column2position(lineno: int, text_original: str, text_dedented: str):
    """the text supplied to parse is 'dedented', and can contain line-breaks,
    so both the reported lineno and character position may be wrong.
    This function updates a mapping of a character to its actual place in the document

    NOTE lineno is in basis 1
    """
    indent = len(text_original) - len(text_original.lstrip())
    # create a mapping of column to doc line/column, taking into account line breaks
    char2docplace = {}
    line_offset = char_count = 0
    for i, char in enumerate(text_dedented):
        char2docplace[i] = (lineno + line_offset, indent + char_count)
        char_count += 1
        if char in ["\n", "\r"]:
            # NOTE: this would not work for the old \n\r mac standard.
            line_offset += 1
            char_count = 0
    return char2docplace


class PositionInliner(Inliner):
    def __init__(self, *, doc_text, **kwargs):
        """Initialise inliner."""
        super().__init__(**kwargs)
        self.content_lines = doc_text.splitlines()
        self.regex_role_start = re.compile("^:([^:]+):.*")
        self.regex_role_end = re.compile(".*:([^:]+):$")

    def parse(
        self, text: str, lineno: int, memo: Any, parent: Any
    ) -> Tuple[List[nodes.Node], List[nodes.system_message]]:
        """
        Return 2 lists: nodes (text and inline elements), and system_messages.

        1. Using `self.patterns.initial`, a pattern which matches start-strings
           (emphasis, strong, interpreted, phrase reference, literal,
           substitution reference, and inline target) and complete constructs
           (simple reference, footnote reference), search for a candidate.
        2. When one is found, check for validity (e.g., not a quoted '*' character).
        3. If valid, search for the corresponding end string if applicable, and
           check it for validity.
        4. If not found or invalid, generate a warning and ignore the start-string.
        5. Implicit inline markup (e.g. standalone URIs) is found last.
        """
        self.reporter = memo.reporter
        self.document = memo.document
        self.language = memo.language
        self.parent = parent
        remaining = escape2null(text)
        processed = []
        unprocessed = []
        messages = []
        current_character = 0
        while remaining:
            match = self.patterns.initial.search(remaining)
            if match:
                groups = match.groupdict()
                method = self.dispatch_methods[
                    groups["start"]
                    or groups["backquote"]
                    or groups["refend"]
                    or groups["fnend"]
                ]
                before, inlines, remaining, sysmessages = method(match, lineno)
                start_character = current_character + len(before)
                end_character = current_character = len(text) - len(remaining)
                inlines = self.record_source_data(
                    lineno=lineno,
                    text=text,
                    start_character=start_character,
                    end_character=end_character,
                    method=method,
                    inlines=inlines,
                )
                unprocessed.append(before)
                messages += sysmessages
                if inlines:
                    processed += self.implicit_inline("".join(unprocessed), lineno)
                    processed += inlines
                    unprocessed = []
            else:
                break
        remaining = "".join(unprocessed) + remaining
        if remaining:
            processed += self.implicit_inline(remaining, lineno)
        return processed, messages

    def record_source_data(
        self,
        lineno: int,
        text: str,
        start_character: int,
        end_character: int,
        method,
        inlines: List[nodes.Node],
    ) -> List[nodes.Node]:

        if not inlines or isinstance(inlines[0], nodes.problematic):
            return inlines

        rawsource = text[start_character:end_character]
        column2position = get_column2position(
            lineno, self.content_lines[lineno - 1], text
        )
        start_lineno, start_char = column2position[start_character]
        end_lineno, end_char = column2position[end_character - 1]
        position = [start_lineno - 1, start_char, end_lineno - 1, end_char]

        method_name = method.__name__
        doc_node = None

        if method_name == "reference":
            doc_node = PosInline(
                position=position,
                rawsource=rawsource,
                children=inlines,
                stype="ref_basic",
            )
        elif method_name == "anonymous_reference":
            doc_node = PosInline(
                position=position,
                rawsource=rawsource,
                children=inlines,
                stype="ref_anon",
            )
        elif method_name == "footnote_reference":
            if isinstance(inlines[0], nodes.citation_reference):
                doc_node = PosInline(
                    position=position,
                    rawsource=rawsource,
                    children=inlines,
                    stype="ref_cite",
                )
            elif isinstance(inlines[0], nodes.footnote_reference):
                doc_node = PosInline(
                    position=position,
                    rawsource=rawsource,
                    children=inlines,
                    stype="ref_foot",
                )
        elif method_name == "substitution_reference":
            doc_node = PosInline(
                position=position,
                rawsource=rawsource,
                children=inlines,
                stype="ref_sub",
            )
        elif method_name == "inline_internal_target":
            doc_node = PosInline(
                position=position,
                rawsource=rawsource,
                children=inlines,
                stype="target_inline",
            )
        elif method_name == "interpreted_or_phrase_ref":
            if rawsource.endswith("_"):
                doc_node = PosInline(
                    position=position,
                    rawsource=rawsource,
                    children=inlines,
                    stype="ref_phrase",
                )
            else:
                role_match = self.regex_role_start.match(
                    rawsource
                ) or self.regex_role_end.match(rawsource)
                role = role_match.group(1) if role_match else ""
                doc_node = PosInline(
                    position=position,
                    rawsource=rawsource,
                    children=inlines,
                    stype="role",
                    role=role,
                )

        return [doc_node] if doc_node is not None else inlines
