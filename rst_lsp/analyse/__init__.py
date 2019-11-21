"""Module for analysing an RST document.

Provides error analysis and analysis of element positions in the document,
in a JSON format compatible with database storage.

Examples
--------

.. code-block: python

    from textwrap import dedent

    source = dedent(
        '''\\
        .. _title:

        Title
        -----

        :ref:`title`
        :cite:`citation`
        :unknown:`abc`

        .. note::

            A note about |RST|

        .. |RST| replace:: ReStructuredText
        '''
    )
    results = assess_source(
        source, confoverrides={"extensions": ["sphinxcontrib.bibtex"]},
    )
    assert results.errors == [
        {
            "line": 6,
            "type": "ERROR",
            "level": 3,
            "description": 'Unknown interpreted text role "unknown".',
        }
    ]
    assert results.elements == [
        {
            "type": "Block",
            "element": "hyperlink_target",
            "start_char": 0,
            "lineno": 1,
            "raw": ".. _title:",
            "target": "title",
        },
        {
            "type": "Block",
            "element": "section",
            "start_char": 0,
            "lineno": 3,
            "level": 1,
            "title": "Title",
        },
        {
            "type": "Inline",
            "element": "role",
            "lineno": 6,
            "start_char": 0,
            "role": "ref",
            "content": "title",
            "raw": ":ref:`title`",
        },
        {
            "type": "Inline",
            "element": "role",
            "lineno": 7,
            "start_char": 0,
            "role": "cite",
            "content": "citation",
            "raw": ":cite:`citation`",
        },
        {
            "type": "Inline",
            "element": "role",
            "lineno": 8,
            "start_char": 0,
            "role": "unknown",
            "content": "abc",
            "raw": ":unknown:`abc`",
        },
        {
            "type": "Block",
            "element": "directive",
            "start_char": 0,
            "lineno": 10,
            "type_name": "versionadded",
            "klass": "sphinx.domains.changeset.VersionChange",
            "arguments": ['1.0'],
            "options": {},
        },
        {
            "type": "Inline",
            "element": "reference",
            "ref_type": "substitution",
            "lineno": 12,
            "start_char": 17,
        },
        {
            "type": "Block",
            "element": "substitution_def",
            "start_char": 0,
            "lineno": 14,
            "raw": ".. |RST| replace:: ReStructuredText",
            "sub": "RST",
        },
        {
            "type": "Block",
            "element": "directive",
            "start_char": 0,
            "lineno": 14,
            "type_name": "replace",
            "klass": "docutils.parsers.rst.directives.misc.Replace",
            "arguments": [],
            "options": {},
        },
    ]

"""
