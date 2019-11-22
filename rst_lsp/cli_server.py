"""Basic CLI implementation of the language-server.

See https://github.com/palantir/python-language-server/blob/develop/pyls/plugins/,
for a relatively complete set of implemented language-server features.

For testing, before implementing actual JSON RPC 2.0 protocol
(see https://github.com/palantir/python-jsonrpc-server)
"""
from functools import update_wrapper
import json
import os
import sys
import textwrap
from typing import Optional

# import attr
import click
import yaml

from rst_lsp import __version__
from rst_lsp.analyse.main import init_sphinx, assess_source
from rst_lsp.database.tinydb import Database
from rst_lsp.docutils_ext.visitor import ElementType


def fetch_db_path():
    return os.environ.get("RST_LSP_DB", os.path.abspath(".rst-lsp-db.json"))
    # return click.prompt(
    #     "Please provide the path to the database.",
    #     default=os.path.abspath("db.json"),
    #     type=str,
    # )


def pass_database(f, database_cls=Database):
    def new_func(*args, **kwargs):
        ctx = click.get_current_context()
        obj = ctx.find_object(database_cls)
        if obj is None:
            path = fetch_db_path()
            ctx.obj = obj = database_cls(path, cache_writes=False)
        if obj is None:
            raise RuntimeError(
                "Managed to invoke callback without a "
                "context object of type %r existing" % database_cls.__name__
            )
        return ctx.invoke(f, obj, *args, **kwargs)

    return update_wrapper(new_func, f)


# @attr.s
# class Document:
#     """A single document."""

#     uri = attr.ib()


# def json2doc(db_data):
#     return Document(uri=db_data["uri"])


def echo_error(text: str):
    click.secho(click.style("ERROR", fg="red") + " " + text)
    sys.exit(2)
    # raise click.ClickException(click.style("ERROR", fg="red") + " " + text)


def echo_success(text: str):
    click.secho(click.style("SUCCESS", fg="green") + " " + text)


def echo_dictionary(dct: dict, as_yaml: bool = False):
    if as_yaml:
        click.echo(yaml.safe_dump(dct))
    else:
        click.echo(json.dumps(dct, indent=2))


def echo_db(database, suppress=False):
    if not suppress:
        click.echo(f"Using database: {database.path}")


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__)
def cli_entry():
    """A CLI implementation of the rst-language-server."""
    pass


def print_help_recurse(command, ctx, indent=0):
    if hasattr(command, "commands"):
        click.secho("\n" + " " * indent + command.name, fg="blue")
        click.secho(" " * indent + "-" * len(command.name), fg="blue")
        click.echo(textwrap.indent(command.get_help(ctx), " " * indent))
        for name, cmnd in command.commands.items():
            print_help_recurse(cmnd, ctx, indent=indent + 2)


@cli_entry.command()
@click.pass_context
def all_help(ctx):
    """Print nested help for all groups."""
    print_help_recurse(cli_entry, ctx)


@cli_entry.group("update")
def group_update():
    """Commands for updating the database, when a file changes."""


@group_update.command("conf-file")
@pass_database
@click.option(
    "--path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
def cmnd_conf_file(database: Database, path: Optional[str]):
    """Update database, for changes in the conf.py file."""
    echo_db(database)
    if path is None:
        pass
    elif os.path.basename(path) != "conf.py":
        echo_error("the file must be named 'conf.py'")
    else:
        path = os.path.dirname(path)
    with init_sphinx(confdir=path) as sphinx_init:
        database.update_conf_file(path, sphinx_init.roles, sphinx_init.directives)
        # TODO this also requires the re-assessment of all source files,
        # but can we be smart about which files to reasses?
        # (e.g. only those containing roles/directives added/removed)
    echo_success(f"updated conf file {path}")


@group_update.command("source-file")
@pass_database
@click.argument("path", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def cmnd_source_file(database: Database, path: str):
    """Update database, for changes in a source (.rst) file."""
    echo_db(database)
    conf_file = database.query_conf_file()
    with click.open_file(path) as handle:
        result = assess_source(
            handle.read(),
            path,
            confdir=os.path.dirname(conf_file["uri"])
            if conf_file is not None
            else None,
        )
    database.update_doc(path, result.elements, result.linting)
    echo_success(f"updated source of {path}")


@cli_entry.group("env")
def group_query_env():
    """Commands for querying the database, for environment data."""


@group_query_env.command("roles")
@pass_database
@click.option(
    "-n", "--name", "names", type=str, multiple=True, help="filter by one or more names"
)
@click.option("--yaml", "as_yaml", is_flag=True, help="return as YAML (default JSON)")
@click.option("--raw", is_flag=True, help="Suppress printing any additional info")
def cmnd_roles(database: Database, names: list, as_yaml: bool, raw: bool):
    """List available roles."""
    echo_db(database, raw)
    roles = database.query_roles(names or None)
    if roles is None:
        echo_error("the role does not exist")
    echo_dictionary([dict(r) for r in roles], as_yaml=as_yaml)


@group_query_env.command("directives")
@pass_database
@click.option(
    "-n", "--name", "names", type=str, multiple=True, help="filter by one or more names"
)
@click.option("--yaml", "as_yaml", is_flag=True, help="return as YAML (default JSON)")
@click.option("--raw", is_flag=True, help="Suppress printing any additional info")
def cmnd_directives(database: Database, names: list, as_yaml: bool, raw: bool):
    """List available directives."""
    echo_db(database, raw)
    directs = database.query_directives(names or None)
    if directs is None:
        echo_error("the role does not exist")
    echo_dictionary([dict(d) for d in directs], as_yaml=as_yaml)


@group_query_env.command("documents")
@pass_database
@click.option("--raw", is_flag=True, help="Suppress printing any additional info")
def cmnd_documents(database: Database, raw: str):
    """List parsed source (rst) documents."""
    echo_db(database, raw)
    docs = database.query_docs()
    if docs is None:
        echo_error("No documents parsed")
    echo_dictionary([dict(d) for d in docs])


@cli_entry.group("query")
def group_query_doc():
    """Commands for querying the database, for document data."""


@group_query_doc.command("element")
@pass_database
@click.argument("name", type=click.Choice([e.value for e in ElementType]))
@click.option("--raw", is_flag=True, help="Suppress printing any additional info")
def cmnd_element(database: Database, name: str, raw: bool):
    """List instances of the element found in the documents."""
    echo_db(database, raw)
    elements = database.query_element(name)
    if elements is None:
        elements = []
    echo_dictionary([dict(e) for e in elements])


@group_query_doc.command("lint")
@pass_database
@click.argument("uri", type=str)
@click.option("--raw", is_flag=True, help="Suppress printing any additional info")
def cmnd_lint(database: Database, uri: str, raw: bool):
    """List all linting issues in a document."""
    echo_db(database, raw)
    issues = database.query_lint(uri)
    if issues is None:
        issues = []
    echo_dictionary([dict(i) for i in issues])
