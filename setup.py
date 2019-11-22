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
    ],
    extras_require={
        "cli": ["click>=7,<8"],
        "jsonrpc": ["python-jsonrpc-server>0.3,<0.4"],
        "testing": ["pytest", "pytest-regressions", "sphinxcontrib-bibtex>=1.0.0"],
        "code_style": ["black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "rst-lsp-cli=rst_lsp.click_cli:cli_entry",
            "rst-lsp-serve=rst_lsp.server.cli_entry:main",
        ]
    },
)
