# ReStructuredText Language Server

## Resources

- docutils
  - [Overview of the Docutils Architecture](http://docutils.sourceforge.net/docs/dev/hacking.html)
  - [Docutils Element Reference](http://docutils.sourceforge.net/docs/ref/doctree.html#id201)
  - [Docutils Transforms](http://docutils.sourceforge.net/docs/ref/transforms.html)
- [Syntax Cheat Sheet](https://thomas-cokelaer.info/tutorials/sphinx/rest_syntax.html)
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