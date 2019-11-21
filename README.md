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
