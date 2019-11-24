try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from typing import Any, List, Optional, Union


class TextDocument(TypedDict):
    uri: str
    languageId: Optional[str]
    version: Optional[int]
    text: Optional[str]


class Position(TypedDict):
    line: int
    character: int


class Range(TypedDict):
    start: Position
    end: Position


class TextEdit(TypedDict):
    range: Range
    newText: str


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
    range: Range
    severity: Optional[int]
    code: Optional[Union[int, str]]
    # A human-readable string describing the source of this
    source: Optional[str]
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
