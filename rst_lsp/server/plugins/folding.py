from . import hookimpl


@hookimpl
def rst_folding_range(document):
    return [
        {
            "kind": "region",
            "startLine": 3,
            "startCharacter": 0,
            "endLine": 12,
            "endCharacter": 0,
        }
    ]
