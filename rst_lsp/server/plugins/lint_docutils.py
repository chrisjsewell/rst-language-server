from typing import List

from rst_lsp.server.workspace import Config, Document
from rst_lsp.server.datatypes import Diagnostic
from rst_lsp.server.constants import DiagnosticSeverity

from . import hookimpl

SEVERITY_MAP = {
    2: DiagnosticSeverity.Warning,
    3: DiagnosticSeverity.Error,
    4: DiagnosticSeverity.Error,
}


@hookimpl
def rst_lint(config: Config, document: Document, is_saved: bool) -> List[Diagnostic]:
    database = document.workspace.database
    uri = document.uri
    results = []
    for lint in database.query_lint(uri):
        results.append(
            {
                "source": "docutils",
                "code": f"D00{lint['level']}",  # TODO better diagnostic codes
                "range": {
                    "start": {"line": lint["line"], "character": 0},
                    "end": {"line": lint["line"], "character": 0},
                },
                "message": lint["description"],
                "severity": SEVERITY_MAP.get(lint["level"], DiagnosticSeverity.Hint),
            }
        )
    return results
