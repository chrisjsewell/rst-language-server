# vscode-client

The vscode-client extension for Visual Studio Code helps you develop
and debug language servers. It lets you run multiple language servers
at once with minimal extra configuration per language.

## Using this extension


1. Follow the [Develop against VS Code instructions](/../../#develop-against-vs-code)
1. Open a `.rst` file and hover over text to start using the RST language server.

To view a language server's stderr output in VSCode, select View → Output.
To debug further, see the "Hacking on this extension" section below.

After updating the binary for a language server (during development or after an upgrade), just kill the process (e.g., `killall rst-lsp-serve`).
VSCode will automatically restart and reconnect to the language server process.

## Adding a language server

Register your language server at the bottom of [`extension.ts`](src/extension.ts).

## Hacking on this extension

1. Run `npm install` in this directory (`vscode-client`).
2. Open this directory by itself in Visual Studio Code.
3. Hit F5 to open a new VSCode instance in a debugger running this extension. (This is equivalent to going to the Debug pane on the left and running the "Launch Extension" task.)

See the [Node.js example language server tutorial](https://code.visualstudio.com/docs/extensions/example-language-server) under "To test the language server" for more information.
