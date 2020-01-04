from importlib import import_module

from setuptools import setup, find_packages


setup(
    name="rst-language-server",
    version=import_module("rst_lsp").__version__,
    author="Chris Sewell",
    packages=find_packages(),
    install_requires=[
        "attrs>=19,<20",
        "sphinx>=2.2,<3",
        "docutils>=0.15.2,<0.16",
        "pyyaml",
        "tinydb>=3.15,<4",
        'typing-extensions; python_version<"3.8"',
    ],
    extras_require={
        "jsonrpc": ["python-jsonrpc-server>0.3,<0.4", "pluggy>=0.13,<0.14"],
        "python_plugins": ["jedi>=0.15", "black>=19,<20"],
        "testing": ["pytest>5,<6", "pytest-regressions", "sphinxcontrib-bibtex>=1.0.0"],
        "code_style": ["black==19.3b0", "pre-commit==1.17.0", "flake8<3.8.0,>=3.7.0"],
    },
    entry_points={
        "console_scripts": [
            "rst-lsp-cli=rst_lsp.click_cli:cli_entry",
            "rst-lsp-serve=rst_lsp.server.cli_entry:main",
        ],
        "rst_lsp": [
            "lint_docutils = rst_lsp.server.plugins.lint_docutils",
            "folding = rst_lsp.server.plugins.folding",
            "completions = rst_lsp.server.plugins.completions",
            "document_symbols = rst_lsp.server.plugins.doc_symbols",
            "hover = rst_lsp.server.plugins.hover",
            "definitions = rst_lsp.server.plugins.definitions",
            "references = rst_lsp.server.plugins.references",
            "format_python = rst_lsp.server.plugins.python_blocks.clens_format",
            "completions_python = rst_lsp.server.plugins.python_blocks.completions",
            "hover_python = rst_lsp.server.plugins.python_blocks.hover",
        ],
    },
)
