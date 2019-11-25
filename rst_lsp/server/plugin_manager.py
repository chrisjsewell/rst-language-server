# TODO annotate hooks
# https://stackoverflow.com/questions/54674679/how-can-i-annotate-types-for-a-pluggy-hook-specification
from enum import Enum
import pkg_resources

# from typing import NamedTuple

import pluggy

PROJECT_NAME = "rst_lsp"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


class PluginTypes(Enum):
    rst_code_actions = "rst_code_actions"
    rst_code_lens = "rst_code_lens"
    rst_commands = "rst_commands"
    rst_completions = "rst_completions"
    rst_definitions = "rst_definitions"
    rst_dispatchers = "rst_dispatchers"
    rst_document_did_open = "rst_document_did_open"
    rst_document_did_save = "rst_document_did_save"
    rst_document_highlight = "rst_document_highlight"
    rst_document_symbols = "rst_document_symbols"
    rst_execute_command = "rst_execute_command"
    rst_experimental_capabilities = "rst_experimental_capabilities"
    rst_folding_range = "rst_folding_range"
    rst_format_document = "rst_format_document"
    rst_format_range = "rst_format_range"
    rst_hover = "rst_hover"
    rst_initialize = "rst_initialize"
    rst_lint = "rst_lint"
    rst_references = "rst_references"
    rst_rename = "rst_rename"
    rst_settings = "rst_settings"
    rst_signature_help = "rst_signature_help"


# _PluginTypesCls = NamedTuple("PluginType", [(n, str) for n in PLUGIN_NAME_LIST])

# PluginTypes = _PluginTypesCls(*[n for n in PLUGIN_NAME_LIST])


class HookSpecs:
    @hookspec
    def rst_code_actions(self, config, workspace, document, range, context):
        pass

    @hookspec
    def rst_code_lens(self, config, workspace, document):
        pass

    @hookspec
    def rst_commands(self, config, workspace):
        """The list of command strings supported by the server.

        Returns:
            List[str]: The supported commands.
        """

    @hookspec
    def rst_completions(self, config, workspace, document, position):
        pass

    @hookspec
    def rst_definitions(self, config, workspace, document, position):
        pass

    @hookspec
    def rst_dispatchers(self, config, workspace):
        pass

    @hookspec
    def rst_document_did_open(self, config, workspace, document):
        pass

    @hookspec
    def rst_document_did_save(self, config, workspace, document):
        pass

    @hookspec
    def rst_document_highlight(self, config, workspace, document, position):
        pass

    @hookspec
    def rst_document_symbols(self, config, workspace, document):
        pass

    @hookspec(firstresult=True)
    def rst_execute_command(self, config, workspace, command, arguments):
        pass

    @hookspec
    def rst_experimental_capabilities(self, config, workspace):
        pass

    @hookspec(firstresult=True)
    def rst_folding_range(self, config, workspace, document):
        pass

    @hookspec(firstresult=True)
    def rst_format_document(self, config, workspace, document):
        pass

    @hookspec(firstresult=True)
    def rst_format_range(self, config, workspace, document, range):
        pass

    @hookspec(firstresult=True)
    def rst_hover(self, config, workspace, document, position):
        pass

    @hookspec
    def rst_initialize(self, config, workspace):
        pass

    @hookspec
    def rst_lint(self, config, workspace, document, is_saved):
        pass

    @hookspec
    def rst_references(
        self, config, workspace, document, position, exclude_declaration
    ):
        pass

    @hookspec(firstresult=True)
    def rst_rename(self, config, workspace, document, position, new_name):
        pass

    @hookspec
    def rst_settings(self, config):
        """Provide initial settings."""
        pass

    @hookspec(firstresult=True)
    def rst_signature_help(self, config, workspace, document, position):
        pass


def create_manager(logger=None):
    manager = pluggy.PluginManager(PROJECT_NAME)
    if logger is not None:
        manager.trace.root.setwriter(logger.debug)
    manager.enable_tracing()
    manager.add_hookspecs(HookSpecs)
    # Pluggy will skip loading a plugin if it throws a DistributionNotFound exception.
    # However we don't all plugins to have to catch ImportError and re-throw.
    # So here we'll filter out any entry points that throw ImportError,
    # assuming one or more of their dependencies isn't present.
    for entry_point in pkg_resources.iter_entry_points(PROJECT_NAME):
        try:
            entry_point.load()
        except ImportError as e:
            if logger is not None:
                logger.warning(
                    "Failed to load %s entry point '%s': %s",
                    PROJECT_NAME,
                    entry_point.name,
                    e,
                )
            manager.set_blocked(entry_point.name)

    # Load the entry points into pluggy, having blocked any failing ones
    manager.load_setuptools_entrypoints(PROJECT_NAME)

    if logger is not None:
        for name, plugin in manager.list_name_plugin():
            if plugin is not None:
                logger.info("Loaded %s plugin %s from %s", PROJECT_NAME, name, plugin)

    return manager
