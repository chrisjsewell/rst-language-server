try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from typing import Any, Dict, List, Optional, Union


class TextDocument(TypedDict):
    uri: str
    languageId: Optional[str]
    version: Optional[int]
    text: Optional[str]


class TextDocumentIdentifier(TypedDict):
    uri: str


class VersionedTextDocumentIdentifier(TypedDict):
    uri: str
    # The version number of a document will increase after each change
    version: Optional[int]


class FileEvent(TypedDict):
    uri: str
    type: int  # created/changed/deleted, 1/2/3, see .constants.FileChangeType


class Position(TypedDict):
    line: int
    character: int


class Range(TypedDict):
    start: Position
    end: Position


class Location(TypedDict):
    uri: str
    range: Range


class TextEdit(TypedDict):
    range: Range
    newText: str


class FoldingRange(TypedDict):

    # The zero-based line number from where the folded range starts.
    startLine: int

    # The zero-based character offset from where the folded range starts.
    # If not defined, defaults to the length of the start line.
    startCharacter: Optional[str]

    # The zero-based line number where the folded range ends.
    endLine: int

    # The zero-based character offset before the folded range ends.
    # If not defined, defaults to the length of the end line.
    endCharacter: Optional[int]

    # Describes the kind of the folding range such as `comment' or 'region'. The kind
    # is used to categorize folding ranges and used by commands like 'Fold all comments'.
    # See FoldingRangeKind for an enumeration of standardized kinds.
    kind: Optional[str]


class CompletionItem(TypedDict):
    label: str
    kind: Optional[int]
    detail: Optional[str]
    documentation: Optional[str]  # or mark-up
    filterText: Optional[str]
    sortText: Optional[str]
    insertText: Optional[str]
    textEdit: Optional[TextEdit]
    additionalTextEdits: Optional[List[TextEdit]]
    insertTextFormat: Optional[int]  # 1=Plain, 2=Snippet
    # optional set of characters that when pressed while this completion is active,
    # will accept it first and then type that character
    commitCharacters: Optional[List[str]]
    command: Optional[Any]  # Command
    deprecated: Optional[bool]
    preselect: Optional[bool]
    sortText: Optional[str]
    filterText: Optional[str]
    data: Optional[Any]


class CompletionList(TypedDict):
    """Represents a collection of [completion items](#CompletionItem) to be presented
    in the editor.
    """

    items: List[CompletionItem]
    isIncomplete: bool


class Diagnostic(TypedDict):
    """Represents a diagnostic, such as a compiler error or warning.
    Diagnostic objects are only valid in the scope of a resource.
    """

    # The range at which the message applies.
    range: Range
    # The diagnostic's severity.
    severity: Optional[int]
    # The diagnostic's code, which might appear in the user interface.
    code: Optional[Union[int, str]]
    # A human-readable string describing the source of this
    # diagnostic, e.g. 'typescript' or 'super lint'.
    source: Optional[str]
    # The diagnostic's message.
    message: str
    # An array of related diagnostic information.
    relatedInformation: Optional[list]


class DocumentSymbol(TypedDict):
    """Represents programming constructs like variables, classes, interfaces etc.
    that appear in a document.
    Document symbols can be hierarchical and they have two ranges:
    one that encloses its definition and one that points to its most interesting range,
    e.g. the range of an identifier.
    """

    # The name of this symbol. Will be displayed in the user interface
    # and therefore must not be
    # an empty string or a string only consisting of white spaces.
    name: str

    # More detail for this symbol, e.g the signature of a function.
    detail: Optional[str]

    # The kind of this symbol.
    kind: int

    # Indicates if this symbol is deprecated.
    deprecated: Optional[bool]

    # The range enclosing this symbol not including leading/trailing whitespace but
    # everything else like comments.
    # This information is typically used to determine if the clients cursor is
    # inside the symbol to reveal in the symbol in the UI.
    range: Range

    # The range that should be selected and revealed when this symbol is being picked,
    # e.g the name of a function. Must be contained by the `range`.
    selectionRange: Range

    # Children of this symbol, e.g. properties of a class.
    children: Optional[list]  # List[DocumentSymbol]


class MarkupContent(TypedDict):
    """Represents a string value which content can be represented in different formats.

    Note that clients might sanitize the return markdown.
    A client could decide to remove HTML from the markdown to avoid script execution.
    """

    # The type of the Markup.
    kind: str  # 'plaintext' | 'markdown'
    # The content itself
    value: str


class MarkedString(TypedDict):
    """Render human readable text

    The language identifier is semantically equal to the optional language identifier,
    in Markdown fenced code blocks
    """

    language: str  # e.g. 'python'
    # The content itself
    value: str


class Hover(TypedDict):
    """The result of a hover request."""

    # The hover's content
    contents: Union[str, MarkupContent, MarkedString, List[MarkedString]]

    # An optional range is a range inside a text document
    # that is used to visualize a hover, e.g. by changing the background color.
    range: Optional[Range]


class Command(TypedDict):
    """Represents a reference to a command.

    Provides a title which will be used to represent a command in the UI.
    Commands are identified by a string identifier.

    The recommended way to handle commands is to implement their execution
    on the server side if the client and server provides the corresponding capabilities.
    Alternatively the tool extension code could handle the command.

    The protocol currently doesn’t specify a set of well-known commands.
    """

    # Title of the command, like `save`.
    title: str
    # The identifier of the actual command handler.
    command: str
    # Arguments that the command handler should be invoked with.
    arguments: Optional[List[Any]]


class CodeLens(TypedDict):
    """
    A code lens represents a command that should be shown along with
    source text, like the number of references, a way to run tests, etc.

    A code lens is _unresolved_ when no command is associated to it. For performance
    reasons the creation of a code lens and resolving should be done in two stages.
    """

    # The range in which this code lens is valid. Should only span a single line.
    range: Range
    # The command this code lens represents.
    command: Optional[Command]
    # A data entry field that is preserved on a code lens item between
    # a code lens and a code lens resolve request.
    data: Optional[Any]


class TextDocumentEdit(TypedDict):
    """Describes textual changes on a single text document.

    The text document is referred to as a VersionedTextDocumentIdentifier,
    to allow clients to check the text document version before an edit is applied.
    A TextDocumentEdit describes all changes on a version Si and after they are applied,
    move the document to version Si+1.
    So the creator of a TextDocumentEdit doesn’t need to sort the array
    or do any kind of ordering. However the edits must be non overlapping.
    """

    # The text document to change.
    textDocument: VersionedTextDocumentIdentifier
    # The edits to be applied.
    edits: List[TextEdit]


class WorkspaceEdit(TypedDict):
    """A workspace edit represents changes to many resources managed in the workspace.

    The edit should either provide changes or documentChanges.
    If the client can handle versioned document edits and if documentChanges are present,
    the latter are preferred over changes.

    Depending on the client capability ``workspace.workspaceEdit.resourceOperations``,
    document changes are either an array of ``TextDocumentEdit``s to express changes to
    *n* different text documents, where each text document edit addresses a
    specific version of a text document.
    Or it can contain above ``TextDocumentEdit``s mixed with
    create, rename and delete file / folder operations.
    Whether a client supports versioned document edits is expressed *via*
    ``workspace.workspaceEdit.documentChanges`` client capability.
    If a client neither supports ``documentChanges`` nor
    ``workspace.workspaceEdit.resourceOperations``, then
    only plain `TextEdit`s using the `changes` property are supported.
    """

    # Holds changes to existing resources. {uri: [text edits]}
    changes: Optional[Dict[str, List[TextEdit]]]

    documentChanges: Optional[List[TextDocumentEdit]]
    # (TextDocumentEdit[] | (TextDocumentEdit | CreateFile | RenameFile | DeleteFile)[])
