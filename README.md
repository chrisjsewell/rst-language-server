# ReStructuredText Language Server

## Resources

- docutils
  - [Overview of the Docutils Architecture](http://docutils.sourceforge.net/docs/dev/hacking.html)
  - [Docutils Element Reference](http://docutils.sourceforge.net/docs/ref/doctree.html#id201)
  - [Docutils Transforms](http://docutils.sourceforge.net/docs/ref/transforms.html)
  - [Parsing Tutorial](https://eli.thegreenplace.net/2017/a-brief-tutorial-on-parsing-restructuredtext-rest/)
- sphinx
  - [Syntax Cheat Sheet](https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html)
  - [Sphinx build phases](https://www.sphinx-doc.org/en/master/extdev/index.html#build-phases)
- [doc8](https://github.com/PyCQA/doc8) RST linter
  - very basic, only accepts docutils directives, doesn't check roles, etc
- [vscode-restructuredtext](https://github.com/vscode-restructuredtext/vscode-restructuredtext)
  - no intellisense
  - decent HTML viewer, but calls sphinx in separate process for each build (not cancelling the last!) and very quickly overloading CPU
  - used doc8 for linting (calling each time in a separate subprocess)
  - [Issue for switching to LSP (2017!)](https://github.com/vscode-restructuredtext/vscode-restructuredtext/issues/73)
- [python-jsonrpc-server](https://github.com/palantir/python-jsonrpc-server)
  - Used to implement LSP server protocol
- [RST Parer for JS (incomplete)](https://github.com/seikichi/restructured)
- It would be ideal to store path/line/character mappings to links, references, etc in a lightweight, pure-python, database, for fast querying.
  - Note sphinx stores a pickled file of each doctree, with a mapping of document names to last updated time, stored in the `app.env.all_docs`, that is pickled to `environment.pickle`. I doubt this contains enough info for such querying though.
  - [tinydb](https://github.com/msiemens/tinydb) (last commit 4 days ago, 3.2K stars, no deps)
  - [pickledb](https://github.com/patx/pickledb) (last commit 4 days ago, 427 stars, no deps)
  - [zodb](https://github.com/zopefoundation/ZODB) (last commit month ago, 358 stars, 8 dependencies)
  - [Flata](https://blog.ruanbekker.com/blog/2018/04/15/experimenting-with-python-and-flata-the-lightweight-document-orientated-database/) (last commit 2017, 12 stars)
  - [Comparison of pickledb/tinydb/zodb](https://opensourceforu.com/2017/05/three-python-databases-pickledb-tinydb-zodb/)
- TexMate Grammar
  - [Guide](https://macromates.com/manual/en/language_grammars)
  - [VSCode Python](https://github.com/microsoft/vscode/blob/master/extensions/python/syntaxes/MagicPython.tmLanguage.json)
  - [Regex Tutorial](https://www.regular-expressions.info/posixbrackets.html)
  - [Writing TexMate Grammar Blog](https://www.apeth.com/nonblog/stories/textmatebundle.html)
  - Multiline captures (not possible?)
    - https://github.com/microsoft/vscode-textmate/issues/41
    - https://github.com/microsoft/vscode-textmate/issues/57
  - [LSP Semantic highlighting feature request](https://github.com/microsoft/language-server-protocol/issues/513)
- Noted issues in the LSP repo
  - [Get all Workspace documents](https://github.com/microsoft/language-server-protocol/issues/837)
  - Progress indicators or coming in LSP version 3.15.0: [Work Done Progress](https://microsoft.github.io/langhttps://microsoft.github.io/language-server-protocol/specifications/specification-3-15/#workDoneProgress)
    - [Discussion: LSP-server readiness indicator](https://github.com/microsoft/language-server-protocol/issues/511)

## Docutils Transforms

Standard transforms from `readers.standalone` (with `default_priority`)

- `transforms.references.Substitutions` (220)
  Replace substitution references by their corresponding definition
- `transforms.references.PropagateTargets` (260)
  Propagate empty internal targets to the next element.
- `transforms.frontmatter.DocTitle` (320)
  Converts an initial section title to a document title
- `transforms.frontmatter.DocInfo` (340)
  Converts an initial field_list to docinfo
- `transforms.frontmatter.SectionSubTitle` (350)
  Converts children sections to subtitles
- `transforms.references.AnonymousHyperlinks` (440)
  Link anonymous references to targets
- `transforms.references.IndirectHyperlinks` (460)
  For targets that refer to other targets (via `refname`),
  replace with the final `refuri` (for external links)
  or a `refid` to the final target (for internal links)
- `transforms.references.Footnotes` (620)
  Assign numbers to autonumbered footnotes,
  and resolve links to footnotes, citations, and their references.
- `transforms.references.ExternalTargets` (640)
  Replace `refname` by `refuri`, for references to external targets
- `transforms.references.InternalTargets` (660)
  Replace `refname` by `refid`, for references to internal targets
- `transforms.universal.StripComments` (740) (from `readers.Reader`)
  Remove comment elements from the document tree
- `transforms.universal.Decorations` (820) (from `readers.Reader`)
  Populate a document's decoration element (header, footer)
- `transforms.misc.Transitions` (830)
  Move transitions (denoted by `----`) at the end of sections up the tree.
  Send `reporter.error` if transition after a title,
  at the beginning or end of the document, and after another transition.
- `transforms.universal.ExposeInternals` (840) (from `readers.Reader`)
- `transforms.references.DanglingReferences` (850)
  Send ``reporter.info`` for any dangling references (including footnote and citation),
  and for unreferenced targets.

### transforms.references.Substitutions

Replace substitution references by their corresponding definition

```xml
<paragraph>
    The
    <substitution_reference refname="biohazard">
        biohazard
        symbol is deservedly scary-looking.
<substitution_definition name="biohazard">
    <image alt="biohazard" uri="biohazard.png">
```

```xml
<paragraph>
    The
    <image alt="biohazard" uri="biohazard.png">
        symbol is deservedly scary-looking.
<substitution_definition name="biohazard">
    <image alt="biohazard" uri="biohazard.png">
```

### transforms.references.PropagateTargets

Propagate empty internal targets to the next element.

```xml
<target ids="internal1" names="internal1">
<target anonymous="1" ids="id1">
<target ids="internal2" names="internal2">
<paragraph>
    This is a test.
```

```xml
<target refid="internal1">
<target anonymous="1" refid="id1">
<target refid="internal2">
<paragraph ids="internal2 id1 internal1" names="internal2 internal1">
    This is a test.
```

### transforms.references.AnonymousHyperlinks

Link anonymous references to targets.

```xml
<paragraph>
    <reference anonymous="1">
        internal
    <reference anonymous="1">
        external
<target anonymous="1" ids="id1">
<target anonymous="1" ids="id2" refuri="http://external">
```

```xml
<paragraph>
    <reference anonymous="1" refid="id1">
        text
    <reference anonymous="1" refuri="http://external">
        external
<target anonymous="1" ids="id1">
<target anonymous="1" ids="id2" refuri="http://external">
```

### transforms.references.IndirectHyperlinks

For targets that refer to other targets (via `refname`), replace with the final `refuri` (for external links) or a `refid` to the final target (for internal links).

External links:

```xml
<paragraph>
    <reference refname="indirect external">
        indirect external
<target id="id1" name="direct external" refuri="http://indirect">
<target id="id2" name="indirect external" refname="direct external">
```

```xml
<paragraph>
    <reference refname="indirect external">
        indirect external
<target id="id1" name="direct external" refuri="http://indirect">
<target id="id2" name="indirect external" refuri="http://indirect">
```

Internal links:

```xml
<target id="id1" name="final target">
<paragraph>
    <reference refname="indirect internal">
        indirect internal
<target id="id2" name="indirect internal 2" refname="final target">
<target id="id3" name="indirect internal" refname="indirect internal 2">
```

```xml
<target id="id1" name="final target">
<paragraph>
    <reference refid="id1">
        indirect internal
<target id="id2" name="indirect internal 2" refid="id1">
<target id="id3" name="indirect internal" refid="id1">
```

### transforms.references.Footnotes

Assign numbers to autonumbered footnotes, and resolve links to footnotes, citations, and their references.

```xml
<paragraph>
    A labeled autonumbered footnote referece:
    <footnote_reference auto="1" id="id1" refname="footnote">
<paragraph>
    An unlabeled autonumbered footnote referece:
    <footnote_reference auto="1" id="id2">
<footnote auto="1" id="id3">
    <paragraph>
        Unlabeled autonumbered footnote.
<footnote auto="1" id="footnote" name="footnote">
    <paragraph>
        Labeled autonumbered footnote.
```

```xml
<paragraph>
    A labeled autonumbered footnote referece:
    <footnote_reference auto="1" id="id1" refid="footnote">
        2
<paragraph>
    An unlabeled autonumbered footnote referece:
    <footnote_reference auto="1" id="id2" refid="id3">
        1
<footnote auto="1" id="id3" backrefs="id2">
    <label>
        1
    <paragraph>
        Unlabeled autonumbered footnote.
<footnote auto="1" id="footnote" name="footnote" backrefs="id1">
    <label>
        2
    <paragraph>
        Labeled autonumbered footnote.
```

### transforms.references.ExternalTargets

Replace `refname` by `refuri`, for references to external targets.

```xml
<paragraph>
    <reference refname="direct external">
        direct external
<target id="id1" name="direct external" refuri="http://direct">
```

```xml
<paragraph>
    <reference refuri="http://direct">
        direct external
<target id="id1" name="direct external" refuri="http://direct">
```

### transforms.references.InternalTargets

Replace `refname` by `refid`, for references to internal targets.

```xml
<paragraph>
    <reference refname="direct internal">
        direct internal
<target id="id1" name="direct internal">
```

```xml
<paragraph>
    <reference refid="id1">
        direct internal
<target id="id1" name="direct internal">
```

### transforms.misc.Transitions

Move transitions (denoted by `--------`) at the end of sections up the tree.
Send `reporter.error` if transition after a title, at the beginning or end of the document, and after another transition.

```xml
<section>
    ...
    <transition>
<section>
    ...
```

```xml
<section>
    ...
<transition>
<section>
    ...
```
