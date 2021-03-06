# Copyright 2017 Palantir Technologies, Inc.
"""Some Language Server Protocol constants
https://github.com/Microsoft/language-server-protocol/blob/master/protocol.md
"""


class CompletionItemKind:
    Text = 1
    Method = 2
    Function = 3
    Constructor = 4
    Field = 5
    Variable = 6
    Class = 7
    Interface = 8
    Module = 9
    Property = 10
    Unit = 11
    Value = 12
    Enum = 13
    Keyword = 14
    Snippet = 15
    Color = 16
    File = 17
    Reference = 18


class DocumentHighlightKind:
    Text = 1
    Read = 2
    Write = 3


class DiagnosticSeverity:
    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


class InsertTextFormat:
    PlainText = 1
    Snippet = 2


class MessageType:
    Error = 1
    Warning = 2
    Info = 3
    Log = 4


class SymbolKind:
    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18


class TextDocumentSyncKind:
    # Documents should not be synced at all
    NONE = 0
    # Documents are synced by always sending the full content
    FULL = 1
    # Documents are synced by sending the full content on open
    # After that only incremental updates to the document are sent
    INCREMENTAL = 2


class FoldingRangeKind:
    Comment = "comment"
    Imports = "imports"
    Region = "region"


class FileChangeType:
    Created = 1
    Changed = 2
    Deleted = 3
