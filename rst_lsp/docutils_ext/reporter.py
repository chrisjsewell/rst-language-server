"""This module provides a custom reporter to capture reports in JSON format."""
from typing import Any, Tuple

from docutils import nodes
from docutils.frontend import OptionParser
from docutils.utils import decode_path, Reporter

__all__ = ("JSONReporter", "new_document")


class JSONReporter(Reporter):
    """Reporter that captures reports as JSON objects

    The captured report is stored in ``JSONReporter.log_capture``.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_capture = []

    def system_message(self, level, message, *children, **kwargs):
        sys_message = super().system_message(level, message, *children, **kwargs)
        if level >= self.report_level:
            self.log_capture.append(
                {
                    # "source": sys_message["source"],
                    "line": sys_message.get("line", ""),
                    "type": sys_message["type"],
                    "level": sys_message["level"],
                    "description": nodes.Element.astext(sys_message),
                }
            )
        return sys_message


JSONReporter.__init__.__doc__ = Reporter.__init__.__doc__


def new_document(
    source_path: str, settings: Any = None
) -> Tuple[nodes.document, JSONReporter]:
    """Return a new empty document object.

    Replicates ``docutils.utils.new_document``, but uses JSONReporter,
    which is also returned

    Parameters
    ----------
    source_path : str
        The path to or description of the source text of the document.
    settings : optparse.Values
        Runtime settings.  If none are provided, a default core set will
        be used.  If you will use the document object with any Docutils
        components, you must provide their default settings as well.  For
        example, if parsing, at least provide the parser settings,
        obtainable as follows::

            settings = docutils.frontend.OptionParser(
                components=(docutils.parsers.rst.Parser,)
                ).get_default_values()
    """
    # TODO cache creation, as in sphinx.util.docutils.new_document, possibly using a
    # 'partial' lru_cache, as in https://stackoverflow.com/a/37611009/5033292
    if settings is None:
        settings = OptionParser().get_default_values()
    # TODO can probably remove decode_path, given python 3 only support
    source_path = decode_path(source_path)
    reporter = JSONReporter(
        source_path,
        settings.report_level,
        settings.halt_level,
        stream=settings.warning_stream,
        debug=settings.debug,
        encoding=settings.error_encoding,
        error_handler=settings.error_encoding_error_handler,
    )
    document = nodes.document(settings, reporter, source=source_path)
    document.note_source(source_path, -1)
    return document, reporter
