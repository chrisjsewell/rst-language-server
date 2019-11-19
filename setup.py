from importlib import import_module

from setuptools import setup, find_packages


setup(
    name="rst-language-server",
    version=import_module("rst_lsp").__version__
    author="Chris Sewell",
    packages=find_packages(),
    install_requires=["sphinx>=2.2,<3", "docutils>=0.15.2,<0.16", "pyyaml"],
    extras_require={
        "testing": ["pytest", "pytest-regressions", "sphinxcontrib-bibtex>=1.0.0"],
        "code_style": ["black", "flake8"],
    },
    entry_points={},
)
