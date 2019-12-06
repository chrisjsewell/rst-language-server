"""This module provides a custom for subclass of ``docutils.parsers.rst.states.Inliner``.

This subclass adds:

- Propagation of the starting line character, for matched patterns.
- injection of ``InfoNodeInline`` docutils elements into the parsed doctree,
  to allow for line numbers and character columns to be obtained, for certain elements,
  during a subsequent ``document.walk``.


"""
from typing import Optional

from docutils import ApplicationError, nodes, utils
from docutils.nodes import fully_normalize_name as normalize_name
from docutils.nodes import whitespace_normalize_name
from docutils.parsers.rst import roles
from docutils.parsers.rst.states import Inliner, MarkupMismatch
from docutils.utils import (
    escape2null,
    punctuation_chars,
    split_escaped_whitespace,
    unescape,
    urischemes,
)

__all__ = ("InfoNodeInline", "LSPInliner")


class InfoNodeInline(nodes.Node):
    """A node for highlighting an inline element position in the document."""

    def __init__(
        self,
        inliner: nodes.Node,
        dtype: str,
        doc_lineno: int,
        doc_char: int,
        raw: str,
        data: Optional[dict] = None,
    ):
        self.parent = inliner.parent
        self.document = inliner.document
        self.dtype = dtype
        self.doc_lineno = doc_lineno
        self.doc_char = doc_char
        self.raw = raw
        self.other_data = data or {}
        self.children = []

    def astext(self):
        return f'<InfoNodeInline "{self.dtype}" doc_line={self.doc_lineno}>'

    def pformat(self, indent="    ", level=0):
        """Return an indented pseudo-XML representation, for test purposes."""
        return indent * level + self.astext() + "\n"

    def __repr__(self):
        return self.astext()

    def shortrepr(self):
        return self.astext()


class LSPInliner(Inliner):
    """Parse inline markup; call the `parse()` method.

    This is a subclass of that propagates the starting character number of elements,
    and records certain elements as data-structures containing this information.
    """

    def __init__(self, doc_text=None):
        """List of (pattern, bound method) tuples, used by
        `self.implicit_inline`."""
        self.implicit_dispatch = []
        if doc_text:
            self.content_lines = doc_text.splitlines()
        else:
            self.content_lines = None

    def update_char2docplace(self, lineno, text):
        """the text supplied to parse is 'dedented', and can contain line-breaks,
        so both the reported lineno and character position may be wrong.
        This function updates a mapping of a character to its actual place in the document

        NOTE lineno are in basis 1
        """
        indent = 0
        if self.content_lines:
            line = self.content_lines[lineno - 1]
            indent = len(line) - len(line.lstrip())
        # create a mapping of column to doc line/column, taking into account line breaks
        self.char2docplace = {}
        line_offset = char_count = 0
        for i, char in enumerate(text):
            self.char2docplace[i] = (lineno + line_offset, indent + char_count)
            char_count += 1
            if char in ["\n", "\r"]:
                # NOTE: this would not work for the old \n\r mac standard.
                line_offset += 1
                char_count = 0

    def parse(self, text, lineno, memo, parent):
        # Needs to be refactored for nested inline markup.
        # Add nested_parse() method?
        """
        Return 2 lists: nodes (text and inline elements), and system_messages.

        Using `self.patterns.initial`, a pattern which matches start-strings
        (emphasis, strong, interpreted, phrase reference, literal,
        substitution reference, and inline target) and complete constructs
        (simple reference, footnote reference), search for a candidate.  When
        one is found, check for validity (e.g., not a quoted '*' character).
        If valid, search for the corresponding end string if applicable, and
        check it for validity.  If not found or invalid, generate a warning
        and ignore the start-string.  Implicit inline markup (e.g. standalone
        URIs) is found last.
        """
        self.update_char2docplace(lineno, text)

        self.reporter = memo.reporter
        self.document = memo.document
        self.language = memo.language
        self.parent = parent
        pattern_search = self.patterns.initial.search
        dispatch = self.dispatch
        remaining = escape2null(text)
        processed = []
        unprocessed = []
        messages = []
        while remaining:
            match = pattern_search(remaining)
            if match:
                groups = match.groupdict()
                method = dispatch[
                    groups["start"]
                    or groups["backquote"]
                    or groups["refend"]
                    or groups["fnend"]
                ]
                before, inlines, remaining, sysmessages = method(
                    self, match, lineno, start_char=len(text) - len(remaining)
                )
                unprocessed.append(before)
                messages += sysmessages
                if inlines:
                    processed += self.implicit_inline(
                        "".join(unprocessed),
                        lineno,
                        start_char=len(text) - len(remaining),
                    )
                    processed += inlines
                    unprocessed = []
            else:
                break
        remaining = "".join(unprocessed) + remaining
        if remaining:
            processed += self.implicit_inline(
                remaining, lineno, start_char=len(text) - len(remaining)
            )
        return processed, messages

    # Inline object recognition
    # ---------------f----------
    # See also init_customizations().
    non_whitespace_before = r"(?<!\s)"
    non_whitespace_escape_before = r"(?<![\s\x00])"
    non_unescaped_whitespace_escape_before = r"(?<!(?<!\x00)[\s\x00])"
    non_whitespace_after = r"(?!\s)"
    # Alphanumerics with isolated internal [-._+:] chars (i.e. not 2 together):
    simplename = r"(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*"
    # Valid URI characters (see RFC 2396 & RFC 2732);
    # final \x00 allows backslash escapes in URIs:
    uric = r"""[-_.!~*'()[\];/:@&=+$,%a-zA-Z0-9\x00]"""
    # Delimiter indicating the end of a URI (not part of the URI):
    uri_end_delim = r"""[>]"""
    # Last URI character; same as uric but no punctuation:
    urilast = r"""[_~*/=+a-zA-Z0-9]"""
    # End of a URI (either 'urilast' or 'uric followed by a
    # uri_end_delim'):
    uri_end = r"""(?:%(urilast)s|%(uric)s(?=%(uri_end_delim)s))""" % locals()
    emailc = r"""[-_!~*'{|}/#?^`&=+$%a-zA-Z0-9\x00]"""
    email_pattern = r"""
          %(emailc)s+(?:\.%(emailc)s+)*   # name
          (?<!\x00)@                      # at
          %(emailc)s+(?:\.%(emailc)s*)*   # host
          %(uri_end)s                     # final URI char
          """

    def quoted_start(self, match):
        """Test if inline markup start-string is 'quoted'.

        'Quoted' in this context means the start-string is enclosed in a pair
        of matching opening/closing delimiters (not necessarily quotes)
        or at the end of the match.
        """
        string = match.string
        start = match.start()
        if start == 0:  # start-string at beginning of text
            return False
        prestart = string[start - 1]
        try:
            poststart = string[match.end()]
        except IndexError:  # start-string at end of text
            return True  # not "quoted" but no markup start-string either
        return punctuation_chars.match_chars(prestart, poststart)

    def inline_obj(
        self,
        match,
        lineno,
        end_pattern,
        nodeclass,
        restore_backslashes=False,
        start_char=None,
    ):
        string = match.string
        matchstart = match.start("start")
        matchend = match.end("start")
        if self.quoted_start(match):
            return (string[:matchend], [], string[matchend:], [], "")
        endmatch = end_pattern.search(string[matchend:])
        if endmatch and endmatch.start(1):  # 1 or more chars
            _text = endmatch.string[: endmatch.start(1)]
            text = unescape(_text, restore_backslashes)
            textend = matchend + endmatch.end(1)
            rawsource = unescape(string[matchstart:textend], True)
            node = nodeclass(rawsource, text)
            node[0].rawsource = unescape(_text, True)
            return (
                string[:matchstart],
                [node],
                string[textend:],
                [],
                endmatch.group(1),
            )
        msg = self.reporter.warning(
            "Inline %s start-string without end-string." % nodeclass.__name__,
            line=lineno,
        )
        text = unescape(string[matchstart:matchend], True)
        rawsource = unescape(string[matchstart:matchend], True)
        prb = self.problematic(text, rawsource, msg)
        return string[:matchstart], [prb], string[matchend:], [msg], ""

    def problematic(self, text, rawsource, message):
        msgid = self.document.set_id(message, self.parent)
        problematic = nodes.problematic(rawsource, text, refid=msgid)
        prbid = self.document.set_id(problematic)
        message.add_backref(prbid)
        return problematic

    def emphasis(self, match, lineno, start_char=None):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
            match, lineno, self.patterns.emphasis, nodes.emphasis, start_char=start_char
        )
        return before, inlines, remaining, sysmessages

    def strong(self, match, lineno, start_char=None):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
            match, lineno, self.patterns.strong, nodes.strong, start_char=start_char
        )
        return before, inlines, remaining, sysmessages

    def interpreted_or_phrase_ref(self, match, lineno, start_char=None):
        end_pattern = self.patterns.interpreted_or_phrase_ref
        string = match.string
        matchstart = match.start("backquote")
        matchend = match.end("backquote")
        rolestart = match.start("role")
        role = match.group("role")
        position = ""
        if role:
            role = role[1:-1]
            position = "prefix"
        elif self.quoted_start(match):
            return (string[:matchend], [], string[matchend:], [])
        endmatch = end_pattern.search(string[matchend:])
        if endmatch and endmatch.start(1):  # 1 or more chars
            textend = matchend + endmatch.end()
            if endmatch.group("role"):
                if role:
                    msg = self.reporter.warning(
                        "Multiple roles in interpreted text (both "
                        "prefix and suffix present; only one allowed).",
                        line=lineno,
                    )
                    text = unescape(string[rolestart:textend], True)
                    prb = self.problematic(text, text, msg)
                    return string[:rolestart], [prb], string[textend:], [msg]
                role = endmatch.group("suffix")[1:-1]
                position = "suffix"
            escaped = endmatch.string[: endmatch.start(1)]
            rawsource = unescape(string[matchstart:textend], True)
            if rawsource[-1:] == "_":
                if role:
                    msg = self.reporter.warning(
                        "Mismatch: both interpreted text role %s and "
                        "reference suffix." % position,
                        line=lineno,
                    )
                    text = unescape(string[rolestart:textend], True)
                    prb = self.problematic(text, text, msg)
                    return string[:rolestart], [prb], string[textend:], [msg]
                return self.phrase_ref(
                    string[:matchstart],
                    string[textend:],
                    rawsource,
                    escaped,
                    unescape(escaped),
                    lineno=lineno,
                    start_char=start_char,
                    match=match,
                )
            else:
                rawsource = unescape(string[rolestart:textend], True)
                nodelist, messages = self.interpreted(
                    rawsource,
                    escaped,
                    role,
                    lineno,
                    start_char=start_char + rolestart,
                    match=match,
                )
                return (string[:rolestart], nodelist, string[textend:], messages)
        msg = self.reporter.warning(
            "Inline interpreted text or phrase reference start-string "
            "without end-string.",
            line=lineno,
        )
        text = unescape(string[matchstart:matchend], True)
        prb = self.problematic(text, text, msg)
        return string[:matchstart], [prb], string[matchend:], [msg]

    def phrase_ref(
        self, before, after, rawsource, escaped, text, lineno, start_char, match
    ):
        match = self.patterns.embedded_link.search(escaped)
        if match:  # embedded <URI> or <alias_>
            text = unescape(escaped[: match.start(0)])
            rawtext = unescape(escaped[: match.start(0)], True)
            aliastext = unescape(match.group(2))
            rawaliastext = unescape(match.group(2), True)
            underscore_escaped = rawaliastext.endswith(r"\_")
            if aliastext.endswith("_") and not (
                underscore_escaped or self.patterns.uri.match(aliastext)
            ):
                aliastype = "name"
                alias = normalize_name(aliastext[:-1])
                target = nodes.target(match.group(1), refname=alias)
                target.indirect_reference_name = aliastext[:-1]
            else:
                aliastype = "uri"
                alias_parts = split_escaped_whitespace(match.group(2))
                alias = " ".join(
                    "".join(unescape(part).split()) for part in alias_parts
                )
                alias = self.adjust_uri(alias)
                if alias.endswith(r"\_"):
                    alias = alias[:-2] + "_"
                target = nodes.target(match.group(1), refuri=alias)
                target.referenced = 1
            if not aliastext:
                raise ApplicationError("problem with embedded link: %r" % aliastext)
            if not text:
                text = alias
                rawtext = rawaliastext
        else:
            target = None
            rawtext = unescape(escaped, True)

        refname = normalize_name(text)
        reference = nodes.reference(
            rawsource, text, name=whitespace_normalize_name(text)
        )
        reference[0].rawsource = rawtext

        doc_lineno, doc_char = self.char2docplace[start_char + len(before)]
        node_list = [
            InfoNodeInline(
                self,
                dtype="phrase_ref",
                doc_lineno=doc_lineno,
                doc_char=doc_char,
                raw=rawsource,
                data=dict(
                    alias=alias,
                    # link_type=ref_type, alt_text=alt_text,
                ),
            ),
            reference,
        ]

        if rawsource[-2:] == "__":
            if target and (aliastype == "name"):
                reference["refname"] = alias
                self.document.note_refname(reference)
                # self.document.note_indirect_target(target) # required?
            elif target and (aliastype == "uri"):
                reference["refuri"] = alias
            else:
                reference["anonymous"] = 1
        else:
            if target:
                target["names"].append(refname)
                if aliastype == "name":
                    reference["refname"] = alias
                    self.document.note_indirect_target(target)
                    self.document.note_refname(reference)
                else:
                    reference["refuri"] = alias
                    self.document.note_explicit_target(target, self.parent)
                # target.note_referenced_by(name=refname)
                node_list.append(target)
            else:
                reference["refname"] = refname
                self.document.note_refname(reference)
        return before, node_list, after, []

    def adjust_uri(self, uri):
        match = self.patterns.email.match(uri)
        if match:
            return "mailto:" + uri
        else:
            return uri

    def interpreted(self, rawsource, text, role, lineno, start_char, match):
        role_fn, messages = roles.role(role, self.language, lineno, self.reporter)
        doc_lineno, doc_char = self.char2docplace[start_char]
        info = InfoNodeInline(
            self,
            dtype="role",
            doc_lineno=doc_lineno,
            doc_char=doc_char,
            raw=rawsource,
            data=dict(role=role, content=text),
        )
        if role_fn:
            nodes, messages2 = role_fn(role, rawsource, text, lineno, self)
            try:
                nodes[0][0].rawsource = unescape(text, True)
            except IndexError:
                pass
            return [info] + nodes, messages + messages2
        else:
            msg = self.reporter.error(
                'Unknown interpreted text role "%s".' % role, line=lineno
            )
            return (
                [info, self.problematic(rawsource, rawsource, msg)],
                messages + [msg],
            )

    def literal(self, match, lineno, start_char=None):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
            match,
            lineno,
            self.patterns.literal,
            nodes.literal,
            restore_backslashes=True,
        )
        return before, inlines, remaining, sysmessages

    def inline_internal_target(self, match, lineno, start_char):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
            match, lineno, self.patterns.target, nodes.target
        )
        if inlines and isinstance(inlines[0], nodes.target):
            assert len(inlines) == 1
            target = inlines[0]
            name = normalize_name(target.astext())
            target["names"].append(name)
            self.document.note_explicit_target(target, self.parent)
            doc_lineno, doc_char = self.char2docplace[start_char + len(before)]
            info = InfoNodeInline(
                self,
                dtype="inline_internal_target",
                doc_lineno=doc_lineno,
                doc_char=doc_char,
                raw=match.string[len(before) : len(match.string) - len(remaining)],
                data={"target": target.astext()},
            )
        return before, [info] + inlines, remaining, sysmessages

    def substitution_reference(self, match, lineno, start_char):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
            match, lineno, self.patterns.substitution_ref, nodes.substitution_reference
        )
        if len(inlines) == 1:
            subref_node = inlines[0]
            if isinstance(subref_node, nodes.substitution_reference):
                subref_text = subref_node.astext()
                self.document.note_substitution_ref(subref_node, subref_text)
                if endstring[-1:] == "_":
                    reference_node = nodes.reference(
                        "|%s%s" % (subref_text, endstring), ""
                    )
                    if endstring[-2:] == "__":
                        reference_node["anonymous"] = 1
                    else:
                        reference_node["refname"] = normalize_name(subref_text)
                        self.document.note_refname(reference_node)
                    reference_node += subref_node
                    inlines = [reference_node]
                doc_lineno, doc_char = self.char2docplace[start_char + len(before)]
                info = InfoNodeInline(
                    self,
                    dtype="substitution_reference",
                    doc_lineno=doc_lineno,
                    doc_char=doc_char,
                    raw=match.string[len(before) : len(match.string) - len(remaining)],
                    data={"target": subref_text},
                )
        return before, [info] + inlines, remaining, sysmessages

    def footnote_reference(self, match, lineno, start_char=None):
        """
        Handles `nodes.footnote_reference` and `nodes.citation_reference`
        elements.
        """
        label = match.group("footnotelabel")
        refname = normalize_name(label)
        string = match.string
        before = string[: match.start("whole")]
        remaining = string[match.end("whole") :]
        if match.group("citationlabel"):
            refnode = nodes.citation_reference("[%s]_" % label, refname=refname)
            refnode += nodes.Text(label)
            self.document.note_citation_ref(refnode)
        else:
            refnode = nodes.footnote_reference("[%s]_" % label)
            if refname[0] == "#":
                refname = refname[1:]
                refnode["auto"] = 1
                self.document.note_autofootnote_ref(refnode)
            elif refname == "*":
                refname = ""
                refnode["auto"] = "*"
                self.document.note_symbol_footnote_ref(refnode)
            else:
                refnode += nodes.Text(label)
            if refname:
                refnode["refname"] = refname
                self.document.note_footnote_ref(refnode)
            if utils.get_trim_footnote_ref_space(self.document.settings):
                before = before.rstrip()
        doc_lineno, doc_char = self.char2docplace[start_char + len(before)]
        info = InfoNodeInline(
            self,
            dtype="footnote_reference",
            doc_lineno=doc_lineno,
            doc_char=doc_char,
            raw=match.string[len(before) : len(match.string) - len(remaining)],
            data={"target": label},
        )
        return (before, [info, refnode], remaining, [])

    def reference(self, match, lineno, anonymous=False, start_char=None):
        referencename = match.group("refname")
        refname = normalize_name(referencename)
        referencenode = nodes.reference(
            referencename + match.group("refend"),
            referencename,
            name=whitespace_normalize_name(referencename),
        )
        referencenode[0].rawsource = referencename
        if anonymous:
            referencenode["anonymous"] = 1
        else:
            referencenode["refname"] = refname
            self.document.note_refname(referencenode)
        string = match.string
        matchstart = match.start("whole")
        matchend = match.end("whole")
        doc_lineno, doc_char = self.char2docplace[start_char + matchstart]
        info = InfoNodeInline(
            self,
            dtype="anonymous_reference" if anonymous else "std_reference",
            doc_lineno=doc_lineno,
            doc_char=doc_char,
            raw=string[matchstart:matchend],
            data={"target": referencename},
        )
        return (string[:matchstart], [info, referencenode], string[matchend:], [])

    def anonymous_reference(self, match, lineno, start_char):
        before, inlines, remaining, msg = self.reference(
            match, lineno, anonymous=1, start_char=start_char
        )
        return (before, inlines, remaining, msg)

    def standalone_uri(self, match, lineno):
        if (
            not match.group("scheme")
            or match.group("scheme").lower() in urischemes.schemes
        ):
            if match.group("email"):
                addscheme = "mailto:"
            else:
                addscheme = ""
            text = match.group("whole")
            unescaped = unescape(text)
            rawsource = unescape(text, True)
            reference = nodes.reference(
                rawsource, unescaped, refuri=addscheme + unescaped
            )
            reference[0].rawsource = rawsource
            return [reference]
        else:  # not a valid scheme
            raise MarkupMismatch

    def pep_reference(self, match, lineno):
        text = match.group(0)
        if text.startswith("pep-"):
            pepnum = int(match.group("pepnum1"))
        elif text.startswith("PEP"):
            pepnum = int(match.group("pepnum2"))
        else:
            raise MarkupMismatch
        ref = (
            self.document.settings.pep_base_url
            + self.document.settings.pep_file_url_template % pepnum
        )
        unescaped = unescape(text)
        return [nodes.reference(unescape(text, True), unescaped, refuri=ref)]

    rfc_url = "rfc%d.html"

    def rfc_reference(self, match, lineno):
        text = match.group(0)
        if text.startswith("RFC"):
            rfcnum = int(match.group("rfcnum"))
            ref = self.document.settings.rfc_base_url + self.rfc_url % rfcnum
        else:
            raise MarkupMismatch
        unescaped = unescape(text)
        return [nodes.reference(unescape(text, True), unescaped, refuri=ref)]

    def implicit_inline(self, text, lineno, start_char=None):
        """
        Check each of the patterns in `self.implicit_dispatch` for a match,
        and dispatch to the stored method for the pattern.  Recursively check
        the text before and after the match.  Return a list of `nodes.Text`
        and inline element nodes.
        """
        if not text:
            return []
        for pattern, method in self.implicit_dispatch:
            match = pattern.search(text)
            if match:
                try:
                    # Must recurse on strings before *and* after the match;
                    # there may be multiple patterns.
                    return (
                        self.implicit_inline(
                            text[: match.start()], lineno, start_char=start_char
                        )
                        + method(match, lineno)
                        + self.implicit_inline(
                            text[match.end() :], lineno, start_char=start_char
                        )
                    )
                except MarkupMismatch:
                    pass
        return [nodes.Text(unescape(text), rawsource=unescape(text, True))]

    dispatch = {
        "*": emphasis,
        "**": strong,
        "`": interpreted_or_phrase_ref,
        "``": literal,
        "_`": inline_internal_target,
        "]_": footnote_reference,
        "|": substitution_reference,
        "_": reference,
        "__": anonymous_reference,
    }
