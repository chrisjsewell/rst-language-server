try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

from typing import Any, List, Optional


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


def CompletionList(TypedDict):
    items: List[CompletionItem]
    isIncomplete: bool
