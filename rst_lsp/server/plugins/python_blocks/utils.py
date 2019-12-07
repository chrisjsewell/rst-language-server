def format_docstring(contents):
    """Python doc strings come in a number of formats, but LSP wants markdown.

    Until we can find a fast enough way of discovering and parsing each format,
    we can do a little better by at least preserving indentation.
    """
    contents = contents.replace("\t", "\u00A0" * 4)
    contents = contents.replace("  ", "\u00A0" * 2)
    return contents
